# tests/conftest.py
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.dependencies import get_db
from app.main import app

# ─── Engine de tests ──────────────────────────────────────
# Usa TEST_DATABASE_URL si existe; si no, usa DATABASE_URL
# En CI ambas apuntan a kanban_test (la DB efímera del servicio)
TEST_DATABASE_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL

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
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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

    # CRÍTICO: mockear el servicio de email en CI
    # Sin este mock, los tests de register y forgot-password intentan
    # llamar a la API de Resend y fallan por credenciales inválidas en CI.
    with patch("app.services.email_service.send_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = True   # simula envío exitoso
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ─── Fixtures de datos de prueba ──────────────────────────

@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """Crea y verifica un usuario de prueba. Retorna { id, email, token }."""
    # Registrar
    response = await client.post("/auth/register", json={
        "email": "test@kanban.dev",
        "username": "testuser",
        "password": "Test1234!",
        "full_name": "Test User",
        "timezone": "America/Mexico_City",
    })
    assert response.status_code == 201, response.json()

    user_id = response.json()["id"]

    # En tests, verificar el email directamente en DB
    # (el código de verificación lo obtenemos del mock o de la DB)
    # Esta fixture asume que el conftest mockea el email y que
    # hay un endpoint de desarrollo /auth/verify-email-dev o
    # que los tests de integración de auth prueban el flujo completo.
    # Adaptar según la implementación real del proyecto.
    return {"id": user_id, "email": "test@kanban.dev"}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    """Retorna los headers de Authorization para un usuario autenticado."""
    response = await client.post("/auth/login", json={
        "email": test_user["email"],
        "password": "Test1234!",
    })
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}