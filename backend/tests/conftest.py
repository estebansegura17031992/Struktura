"""
Configuración global de tests.
- TESTING=True desactiva rate limiting en todos los endpoints.
- Usa kanban_test_db separada de kanban_db.
- Crea ENUMs, tablas e inserta system_settings antes de la sesión.
- Trunca tablas entre tests para aislamiento completo.
"""
import asyncio
import os
 
# ── Desactivar rate limiting ANTES de importar la app ─────────────────────────
os.environ["TESTING"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "false"
 
# Limpiar lru_cache de settings para que tome los nuevos env vars
from app.core import config as _config_module
_config_module.get_settings.cache_clear()
 
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
 
from app.core.config import settings
from app.db.base import Base
import app.db.registry  # noqa: F401 — registra todos los modelos en Base.metadata
from app.main import app
from app.api.deps.db import get_db
 
# ── DB de test ─────────────────────────────────────────────────────────────────
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/kanban_db", "/kanban_test_db")
 
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
 
 
# ── Setup único por sesión de pytest ───────────────────────────────────────────
 
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
 
        for sql in [
            "DO $$ BEGIN CREATE TYPE user_role AS ENUM ('viewer','editor','admin'); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
            "DO $$ BEGIN CREATE TYPE member_role AS ENUM ('owner','editor','viewer'); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
            "DO $$ BEGIN CREATE TYPE invitation_status AS ENUM ('pending','accepted','rejected','expired'); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
            "DO $$ BEGIN CREATE TYPE task_priority AS ENUM ('low','medium','high'); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
            "DO $$ BEGIN CREATE TYPE task_status AS ENUM ('abierto','en_proceso','completo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
            "DO $$ BEGIN CREATE TYPE mention_type AS ENUM ('user','task'); EXCEPTION WHEN duplicate_object THEN NULL; END $$",
        ]:
            await conn.execute(text(sql))
 
        await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS task_number_seq START 1"))
        await conn.run_sync(Base.metadata.create_all)
 
        await conn.execute(text("""
            INSERT INTO system_settings (key, value, description) VALUES
                ('max_projects_per_user', '20', 'Max proyectos'),
                ('max_timer_hours', '12', 'Max horas timer'),
                ('invitation_expiry_days', '7', 'Dias invitacion'),
                ('max_task_assignees', '10', 'Max asignados')
            ON CONFLICT (key) DO NOTHING
        """))
 
    yield
 
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP SEQUENCE IF EXISTS task_number_seq"))
        for enum in ["mention_type","task_status","task_priority",
                     "invitation_status","member_role","user_role"]:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum} CASCADE"))
 
 
# ── Limpieza entre tests ───────────────────────────────────────────────────────
 
@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with test_engine.begin() as conn:
        for table in [
            "comment_mentions","task_comments","task_time_entries",
            "task_assignees","tasks","project_invitations","project_members",
            "projects","audit_logs","password_reset_tokens",
            "refresh_tokens","email_verification_tokens","users",
        ]:
            await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
 
 
# ── Fixtures ───────────────────────────────────────────────────────────────────
 
@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session
 
 
@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session
 
    app.dependency_overrides[get_db] = override_get_db
 
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac
 
    app.dependency_overrides.clear()