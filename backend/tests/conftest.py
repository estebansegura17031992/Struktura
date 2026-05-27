# tests/conftest.py
"""
Estrategia robusta contra el bug de event loop de pytest-asyncio + asyncpg:

PROBLEMA: con asyncio_mode="auto", cada TEST corre en un event loop de scope
'function', pero un engine de scope 'session' crea sus conexiones asyncpg en
el loop de la fixture de sesión. Son loops distintos → "Future attached to a
different loop".

SOLUCIÓN: el engine se crea POR TEST (scope function) con NullPool, de modo
que cada conexión asyncpg nace y muere en el MISMO loop que el test.
Las migraciones se aplican UNA vez a nivel de sesión vía un engine síncrono
(psycopg2), que no tiene problemas de loop.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from alembic.config import Config
from app.api.deps.db import get_db
from app.core.config import settings
from app.db import registry  # noqa: F401 — registra modelos para Alembic
from app.main import app

TEST_DATABASE_URL = (
    getattr(settings, "TEST_DATABASE_URL", None) or settings.DATABASE_URL
)

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


# ─── Migraciones: una sola vez por sesión (SÍNCRONO, sin event loop) ──────


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations():
    """
    Aplica migraciones Alembic una vez al inicio de la sesión usando
    psycopg2 (síncrono). No toca asyncio, así que no hay conflicto de loop.
    """
    alembic_cfg = Config("alembic.ini")

    # Reset schema limpio antes de migrar (vía psycopg2 síncrono)
    from sqlalchemy import create_engine

    sync_url = settings.DATABASE_URL_SYNC
    sync_engine = create_engine(sync_url)
    with sync_engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    sync_engine.dispose()

    command.upgrade(alembic_cfg, "head")

    yield

    # Cleanup final
    sync_engine = create_engine(sync_url)
    with sync_engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    sync_engine.dispose()


# ─── Engine POR TEST con NullPool ─────────────────────────────────────────


@pytest_asyncio.fixture
async def db_engine():
    """
    Engine nuevo para CADA test, con NullPool: cada conexión asyncpg se abre
    y cierra dentro del mismo event loop del test. Sin conexiones persistentes
    entre loops → sin "different loop" ni "operation in progress".
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,  # CLAVE: sin pool, conexión fresca por uso
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# ─── Limpieza entre tests ─────────────────────────────────────────────────


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_engine):
    """
    Trunca todas las tablas ANTES de cada test para garantizar estado limpio.
    Truncar antes (no después) es más robusto: no depende del orden de teardown
    ni de que el test anterior haya terminado de cerrar conexiones.
    """
    async with db_engine.connect() as conn:
        tables = ", ".join(_TRUNCATE_TABLES)
        try:
            await conn.execute(
                text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
    yield


# ─── Sesión por test ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


# ─── Clientes HTTP ────────────────────────────────────────────────────────


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


# ─── Datos de prueba ──────────────────────────────────────────────────────


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
