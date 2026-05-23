"""Dependency — sesión de base de datos por request."""
from typing import AsyncGenerator
 
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.db.session import get_session_factory
 
 
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Inyecta una AsyncSession por request.
    Usa get_session_factory() lazy para evitar fallos en import time.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
