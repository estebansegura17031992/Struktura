"""
Motor async SQLAlchemy + sessionmaker.

IMPORTANTE:
- DATABASE_URL debe usar prefijo postgresql+asyncpg:// (driver async)
- DATABASE_URL_SYNC usa postgresql:// (psycopg2, solo para Alembic)
- En staging/production se usa NullPool — Supabase PgBouncer lo requiere
- El engine se crea lazy (al primer uso) para evitar fallos en import time
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@lru_cache(maxsize=1)
def get_engine():
    """
    Crea el engine una sola vez (singleton).
    Se llama en el primer request, no en import time,
    garantizando que las variables de entorno ya están disponibles.
    """
    # Import aquí para evitar importación circular en tiempo de módulo
    from app.core.config import settings

    # Validar que la URL tiene el driver correcto
    url = settings.DATABASE_URL
    if not url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            f"DATABASE_URL debe comenzar con 'postgresql+asyncpg://', "
            f"valor actual: '{url[:30]}...'. "
            f"Corregir en las variables de entorno."
        )

    if settings.is_production:
        # NullPool requerido por Supabase PgBouncer Transaction mode
        return create_async_engine(url, echo=False, poolclass=NullPool)
    else:
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )


def get_session_factory():
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# AsyncSessionLocal sigue disponible para compatibilidad con código existente
# pero ahora se resuelve lazy al primer acceso
class _LazySessionLocal:
    """Proxy lazy para AsyncSessionLocal — resuelve el factory al primer uso."""

    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)

    def __call__(self):
        return get_session_factory()()


AsyncSessionLocal = get_session_factory
