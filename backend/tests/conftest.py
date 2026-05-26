# tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
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

# ─── URL de tests ────────────────────────────────────────
TEST_DATABASE_URL = (
    getattr(settings, "TEST_DATABASE_URL", None) or settings.DATABASE_URL
)


# ─── Helpers de migración ─────────────────────────────────


def run_alembic_upgrade() -> None:
    """Aplica todas las migraciones incluyendo la creación de ENUMs."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


# ─── Fixtures ─────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Fixture de event loop compartido por toda la sesión de tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    Engine creado DENTRO del fixture de sesión, garantizando que se usa
    el mismo event loop que pytest-asyncio crea para la sesión.
    Crear el engine a nivel de módulo es la causa del error
    'Future attached to a different loop'.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    # Limpiar schema antes de empezar
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.commit()

    # Aplicar migraciones en hilo separado (Alembic es síncrono)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_alembic_upgrade)

    yield engine

    # Limpiar al finalizar
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.commit()

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión de DB con rollback automático después de cada test."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP con DB override y emails mockeados.
    """

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
    """
    Cliente HTTP SIN override de DB — para tests que verifican la DB real
    (ej: /health que hace SELECT 1 contra PostgreSQL).
    """
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


# ─── Fixtures de datos de prueba ──────────────────────────


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """Crea un usuario de prueba. Retorna { id, email }."""
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
    """Retorna los headers de Authorization para un usuario autenticado."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": "Test1234!",
        },
    )
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
