"""
Motor async SQLAlchemy + sessionmaker.
Pool configurado para Supabase free tier: pool_size=10, max_overflow=5 (R-0906).
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
 
from app.core.config import settings
 
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,   # valida conexiones antes de usarlas
)
 
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
