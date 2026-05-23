"""
Health check endpoint (R-0804).
GET /health — público, sin autenticación.
Verifica conectividad con la base de datos.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.api.deps.db import get_db
from app.core.config import settings
 
router = APIRouter()
 
 
@router.get("/health", tags=["system"])
async def health(db: AsyncSession = Depends(get_db)):
    """
    Retorna el estado del servicio y la conectividad con la DB.
    Usado por Railway para health checks y por el equipo para validar deploys.
    """
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
 
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db": db_status,
    }
