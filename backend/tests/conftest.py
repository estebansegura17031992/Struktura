# tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps.db import get_db
from app.core.config import settings
from app.db.base import Base
from app.main import app

# ─── Engine de tests ──────────────────────────────────────
TEST_DATABASE_URL = (
    getattr(settings, "TEST_DATABASE_URL", None) or settings.DATABASE_URL
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Fixtures ─────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Fixture de event loop compartido por toda la sesión de tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Crea las tablas antes de todos los tests y las elimina al final."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # DROP SCHEMA CASCADE evita el error de foreign keys al limpiar
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Sesión de DB con rollback automático después de cada test."""
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP de tests.
    Sobreescribe get_db para usar la sesión de tests con rollback.
    Mockea el servicio de email para que no se envíen emails reales en CI.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch(
        "app.services.email_service.send_email", new_callable=AsyncMock
    ) as mock_email:
        mock_email.return_value = True
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ─── Fixtures de datos de prueba ──────────────────────────


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """Crea un usuario de prueba. Retorna { id, email }."""
    response = await client.post(
        "/auth/register",
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
        "/auth/login",
        json={
            "email": test_user["email"],
            "password": "Test1234!",
        },
    )
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
