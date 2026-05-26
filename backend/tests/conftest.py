# tests/conftest.py
"""
pytest-asyncio >= 0.24 introduce loop_scope para fixtures de sesión.
Con asyncio_default_fixture_loop_scope = "session" en pyproject.toml,
todos los fixtures async comparten el mismo event loop — resuelve el
error "Future attached to a different loop" de la versión 0.23.

Ya no se necesita el fixture event_loop custom ni scope tricks.
"""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from alembic.config import Config
from app.api.deps.db import get_db
from app.core.config import settings
from app.db import registry  # noqa: F401 — registra todos los modelos para Alembic
from app.main import app

TEST_DATABASE_URL = (
    getattr(settings, "TEST_DATABASE_URL", None) or settings.DATABASE_URL
)

# Tablas en orden que respeta FK — se truncan entre tests
_TRUNCATE_TABLES = [
    "audit_logs",
    "password_reset_tokens",
    "email_verification_tokens",
    "refresh_tokens",
    "task_assignees",
    "tasks",
    "columns",
    "projects",
    "users",
]


def _run_alembic_upgrade() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


# ─── Engine y migraciones — scope session ────────────────


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    Engine creado una sola vez para toda la sesión.
    Con pytest-asyncio 0.24 + asyncio_default_fixture_loop_scope="session"
    este fixture comparte el mismo loop que todos los tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=0,
    )

    # Reset schema limpio
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.commit()

    # Alembic es síncrono — corre en executor
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_alembic_upgrade)

    yield engine

    # Teardown: cerrar todas las conexiones del pool antes de DROP
    await engine.dispose()

    cleanup_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    try:
        async with cleanup_engine.connect() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.commit()
    finally:
        await cleanup_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(db_engine):
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# ─── Limpieza entre tests ─────────────────────────────────


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_engine):
    """Trunca todas las tablas DESPUÉS de cada test."""
    yield
    async with db_engine.connect() as conn:
        tables = ", ".join(_TRUNCATE_TABLES)
        try:
            await conn.execute(
                text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
            )
            await conn.commit()
        except Exception:
            await conn.rollback()


# ─── Sesión por test ──────────────────────────────────────


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Sesión fresca por test — sin rollback (lo maneja clean_tables)."""
    async with session_factory() as session:
        yield session


# ─── Clientes HTTP ────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch(
            "app.services.auth_service.send_verification_email",
            new_callable=AsyncMock,
        ) as mock_verify,
        patch(
            "app.services.auth_service.send_reset_password_email",
            new_callable=AsyncMock,
        ) as mock_reset,
    ):
        mock_verify.return_value = None
        mock_reset.return_value = None
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_db_override() -> AsyncGenerator[AsyncClient, None]:
    """Para tests de /health que usan la DB real."""
    with (
        patch(
            "app.services.auth_service.send_verification_email",
            new_callable=AsyncMock,
        ) as mock_verify,
        patch(
            "app.services.auth_service.send_reset_password_email",
            new_callable=AsyncMock,
        ) as mock_reset,
    ):
        mock_verify.return_value = None
        mock_reset.return_value = None
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


# ─── Datos de prueba ──────────────────────────────────────


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@kanban.dev",
            "username": "testuser",
            "password": "Test1234!",
            "full_name": "Test User",
            "timezone": "America/Mexico_City",
        },
    )
    assert response.status_code == 201, response.json()
    return {"id": response.json()["id"], "email": "test@kanban.dev"}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": "Test1234!"},
    )
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
