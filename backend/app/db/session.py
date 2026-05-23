"""
Motor async SQLAlchemy + sessionmaker.

Supabase usa PgBouncer como connection pooler. En modo Transaction (puerto 6543)
no soporta pool_size/max_overflow de SQLAlchemy — hay que usar NullPool.
En desarrollo local se mantiene el pool normal para mejor rendimiento.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Supabase Transaction pooler requiere NullPool
# En staging/production no usar el pool de SQLAlchemy — PgBouncer lo maneja
if settings.is_production:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)