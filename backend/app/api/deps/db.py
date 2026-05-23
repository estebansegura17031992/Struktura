"""Dependency — sesión de base de datos por request."""
from typing import AsyncGenerator
 
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.db.session import AsyncSessionLocal
 
 
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Inyecta una sesión AsyncSession por request.
    La sesión se cierra automáticamente al finalizar el request,
    incluso si ocurre una excepción.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
