"""
Endpoints de perfil de usuario (R-0108).
PATCH /users/me    — editar nombre y timezone
POST  /users/me/change-password — cambiar contraseña (revoca todas las sesiones)
GET   /users/me    — obtener perfil actual
"""

from fastapi import APIRouter, Request

from app.api.deps.auth import DB, CurrentUser
from app.core.exceptions import InvalidCredentialsError
from app.core.security import hash_password, verify_password
from app.repositories.auth_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdateRequest
from app.services.audit_service import log_action
from app.utils.timezone import validate_timezone

router = APIRouter(prefix="/users", tags=["users"])


# ── GET /users/me ──────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Retorna el perfil del usuario autenticado."""
    return UserResponse.model_validate(current_user)


# ── PATCH /users/me ────────────────────────────────────────────────────────────


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: CurrentUser,
    db: DB,
):
    """
    Edita nombre completo y/o timezone del usuario.
    - No se puede cambiar email ni username en MVP (R-0108).
    - Timezone debe ser una entrada válida de la IANA timezone database (AG-02).
    """
    updates: dict = {}

    if body.full_name is not None:
        updates["full_name"] = body.full_name

    if body.timezone is not None:
        validate_timezone(body.timezone)  # lanza InvalidTimezoneError si es inválida
        updates["timezone"] = body.timezone

    if not updates:
        return UserResponse.model_validate(current_user)

    repo = UserRepository(db)
    updated = await repo.update_fields(current_user.id, **updates)
    await db.commit()

    return UserResponse.model_validate(updated)


# ── POST /users/me/change-password ────────────────────────────────────────────


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DB,
):
    """
    Cambia la contraseña del usuario autenticado.
    - Requiere la contraseña actual como verificación.
    - Revoca TODOS los refresh tokens activos del usuario (R-0108).
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise InvalidCredentialsError()

    repo = UserRepository(db)
    refresh_repo = RefreshTokenRepository(db)

    await repo.update_fields(
        current_user.id,
        hashed_password=hash_password(body.new_password),
    )

    # Revocar todas las sesiones activas
    await refresh_repo.revoke_all_for_user(current_user.id)

    ip = request.client.host if request.client else None
    await log_action(
        db,
        "password_change",
        user_id=current_user.id,
        entity_type="user",
        entity_id=current_user.id,
        ip_address=ip,
    )

    await db.commit()
    return MessageResponse(
        message="Contraseña actualizada. Todas las sesiones han sido cerradas."
    )
