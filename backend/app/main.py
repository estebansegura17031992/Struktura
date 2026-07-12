"""
Kanban MVP — FastAPI application entry point.
Sprint 1: health check, CORS, manejo global de errores, rate limiting, logging.
"""

from collections.abc import MutableMapping
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppBaseError
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory
from app.services.timer_service import TimerService

configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)


# ── Security headers — Pure ASGI middleware ────────────────────────────────────
class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                raw_headers: list = list(message.get("headers", []))
                raw_headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"strict-origin"),
                    ]
                )
                message["headers"] = raw_headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


async def _close_orphaned_timers_job() -> None:
    """Sprint 4 · Objetivo 4 — corre cada 15 min, cierra timers activos más
    viejos que system_settings.max_timer_hours. Sesión propia (no
    request-scoped): el scheduler vive fuera del ciclo de vida de un
    request HTTP."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = TimerService(session)
        closed = await service.close_orphaned_timers()
        if closed:
            logger.info("orphaned_timers_closed", count=closed)


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    # No arrancar el scheduler en tests — ASGITransport (httpx) sin
    # asgi-lifespan nunca dispara este contexto, pero el guard queda como
    # segunda barrera explícita si eso cambia.
    if not settings.TESTING:
        scheduler.add_job(
            _close_orphaned_timers_job,
            "interval",
            minutes=15,
            id="close_orphaned_timers",
        )
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("shutdown", app=settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ── CORS (R-0904) ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security headers (R-0904) ──────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Manejo global de errores (R-0804) ──────────────────────────────────────────
@app.exception_handler(AppBaseError)
async def app_exception_handler(request: Request, exc: AppBaseError) -> JSONResponse:
    logger.warning(
        "app_error", code=exc.code, message=exc.message, path=str(request.url)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", error=str(exc), path=str(request.url))
    message = str(exc) if settings.DEBUG else "Error interno del servidor"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": message}},
    )
