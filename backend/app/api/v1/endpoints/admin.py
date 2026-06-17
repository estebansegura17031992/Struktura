"""
Endpoints de administración de usuarios (E02 · ART-04 · R-0204).

GET  /api/v1/admin/users                 — listado paginado de usuarios
PATCH /api/v1/admin/users/{user_id}/role — cambio de rol con validación último admin

Usa AdminUser (require_role("admin")) de app/api/deps/auth.py.
Usa log_action de app/services/audit_service.py.
"""

import math
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select, update

from app.api.deps.auth import DB, AdminUser, CurrentUser
from app.core.exceptions import AppBaseError, UserNotFoundError
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


# ── Schemas inline ────────────────────────────────────────────────────────────


class ChangeRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"viewer", "editor", "admin"}:
            raise ValueError("Rol inválido. Permitidos: viewer, editor, admin")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    _: AdminUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
):
    """
    Lista todos los usuarios del sistema (activos y eliminados).
    Solo accesible para admins. Paginado con wrapper estándar.
    R-0204
    """
    page_size = min(max(page_size, 1), 100)

    total_result = await db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = list(result.scalars().all())
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    current_user: CurrentUser,
    _: AdminUser,
    db: DB,
):
    """
    Cambia el rol de un usuario.
    Validación crítica: no se puede degradar al único admin del sistema.
    Registra en audit_logs con old_role y new_role.
    R-0204
    """
    # Obtener usuario target
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    target = result.scalar_one_or_none()
    if not target:
        raise UserNotFoundError()

    # Sin cambio real — idempotente
    if target.role == body.role:
        return UserResponse.model_validate(target)

    # Validar que no se quede el sistema sin admins (CANNOT_REMOVE_LAST_ADMIN)
    if target.role == "admin" and body.role != "admin":
        count_result = await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.deleted_at.is_(None))
        )
        admin_count = count_result.scalar_one()
        if admin_count <= 1:
            raise AppBaseError(
                "CANNOT_REMOVE_LAST_ADMIN",
                "No se puede degradar al único administrador del sistema.",
                422,
            )

    old_role = target.role

    await db.execute(update(User).where(User.id == user_id).values(role=body.role))
    await db.flush()

    await log_action(
        db,
        "role_changed",
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "old_role": old_role,
            "new_role": body.role,
            "target_username": target.username,
        },
    )

    await db.commit()

    # Refrescar el objeto para retornar el estado actualizado
    result = await db.execute(select(User).where(User.id == user_id))
    updated = result.scalar_one()

    logger.info(
        "role_changed",
        actor_id=str(current_user.id),
        target_id=str(user_id),
        old_role=old_role,
        new_role=body.role,
    )

    return UserResponse.model_validate(updated)
