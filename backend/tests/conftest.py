# tests/conftest.py
"""
Estrategia robusta contra el bug de event loop de pytest-asyncio + asyncpg:

PROBLEMA: con asyncio_mode="auto", cada TEST corre en un event loop de scope
'function', pero un engine de scope 'session' crea sus conexiones asyncpg en
el loop de la fixture de sesiÃ³n. Son loops distintos â†’ "Future attached to a
different loop".

SOLUCIÃ“N: el engine se crea POR TEST (scope function) con NullPool, de modo
que cada conexiÃ³n asyncpg nace y muere en el MISMO loop que el test.
Las migraciones se aplican UNA vez a nivel de sesiÃ³n vÃ­a un engine sÃ­ncrono
(psycopg2), que no tiene problemas de loop.
"""

import os
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
from app.db import registry  # noqa: F401 â€” registra modelos para Alembic
from app.main import app

TEST_DATABASE_URL = getattr(settings, "TEST_DATABASE_URL", None)
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL no esta configurada en .env. Los tests truncan "
        "TODAS las tablas antes de cada test (clean_tables) - configurar una "
        "DB de test separada antes de correr la suite (ver README)."
    )
if TEST_DATABASE_URL == settings.DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL apunta a la MISMA base que DATABASE_URL. Esto "
        "truncaria la base de datos de desarrollo. Usar una DB de test distinta."
    )


# â”€â”€â”€ Migraciones: una sola vez por sesiÃ³n (SÃNCRONO, sin event loop) â”€â”€â”€â”€â”€â”€


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations():
    """
    Aplica migraciones Alembic una vez al inicio de la sesiÃ³n usando
    psycopg2 (sÃ­ncrono). No toca asyncio, asÃ­ que no hay conflicto de loop.
    """
    alembic_cfg = Config("alembic.ini")

    # Reset schema limpio antes de migrar (vÃ­a psycopg2 sÃ­ncrono)
    from sqlalchemy import create_engine

    sync_url = getattr(settings, "TEST_DATABASE_URL_SYNC", None)
    if not sync_url:
        pytest.exit(
            "TEST_DATABASE_URL_SYNC no esta configurada en .env. "
            "Los tests hacen DROP SCHEMA CASCADE - configurar una DB de test "
            "separada antes de correr la suite (ver README).",
            returncode=1,
        )
    if sync_url == settings.DATABASE_URL_SYNC:
        pytest.exit(
            "TEST_DATABASE_URL_SYNC apunta a la MISMA base que DATABASE_URL_SYNC. "
            "Esto borraria la base de datos de desarrollo. Usar una DB de test distinta.",
            returncode=1,
        )
    sync_engine = create_engine(sync_url)
    with sync_engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    sync_engine.dispose()

    os.environ["ALEMBIC_DATABASE_URL_SYNC"] = sync_url
    command.upgrade(alembic_cfg, "head")

    yield

    # Cleanup final
    sync_engine = create_engine(sync_url)
    with sync_engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    sync_engine.dispose()


# â”€â”€â”€ Engine POR TEST con NullPool â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest_asyncio.fixture
async def db_engine():
    """
    Engine nuevo para CADA test, con NullPool: cada conexiÃ³n asyncpg se abre
    y cierra dentro del mismo event loop del test. Sin conexiones persistentes
    entre loops â†’ sin "different loop" ni "operation in progress".
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,  # CLAVE: sin pool, conexiÃ³n fresca por uso
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


# â”€â”€â”€ Limpieza entre tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_engine):
    """
    Trunca TODAS las tablas reales del schema antes de cada test.
    Descubre las tablas dinÃ¡micamente (sin lista hardcoded) para no fallar
    silenciosamente si un nombre no coincide. Excluye alembic_version.
    """
    async with db_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' "
                "AND tablename != 'alembic_version'"
            )
        )
        tables = [row[0] for row in result.fetchall()]
        if tables:
            quoted = ", ".join(f'"{t}"' for t in tables)
            await conn.execute(
                text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
            )
            await conn.commit()
    yield


# â”€â”€â”€ SesiÃ³n por test â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


# â”€â”€â”€ Clientes HTTP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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


# â”€â”€â”€ Datos de prueba â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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
