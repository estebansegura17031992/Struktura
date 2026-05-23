"""
Kanban MVP — FastAPI application entry point.
Sprint 1: health check, CORS, manejo global de errores, rate limiting, logging.
"""
from contextlib import asynccontextmanager
 
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
 
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.api.v1.router import api_router
 
configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)
 
limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, version=settings.APP_VERSION,
                environment=settings.ENVIRONMENT)
    yield
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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
 
# ── CORS (R-0904) ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(api_router)
 
 
# ── Manejo global de errores (R-0804) ──────────────────────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("app_error", code=exc.code, message=exc.message,
                   path=str(request.url))
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
 
 
# ── Security headers (R-0904) ──────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin"
    return response
