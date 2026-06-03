"""
Servicio de auditoría — escritura asíncrona sin bloquear el response (R-0801).
Nunca incluir datos sensibles en metadata.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import AuditLog

logger = get_logger(__name__)


async def log_action(
    session: AsyncSession,
    action: str,
    user_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Registra una acción en audit_logs de forma asíncrona.
    El try/except garantiza que un fallo en auditoría nunca rompa el flujo principal.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            extra_data=metadata,  # columna "metadata" en DB, atributo extra_data en ORM
            ip_address=ip_address,
        )
        session.add(entry)
        # No hacemos flush aquí — se consolida en el commit de la transacción principal
    except Exception as e:
        logger.error("audit_log_failed", action=action, error=str(e))
