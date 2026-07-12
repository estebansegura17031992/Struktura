"""Aceptar/rechazar invitaciones a proyecto — E03 · Sprint 4 · Objetivo 8.

Vive en su propio router (no bajo /projects/{id}) porque el token es
suficiente para resolver todo — no hay project_id en la URL. Requiere
usuario autenticado: si el destinatario no tenía cuenta, el flujo lo lleva
primero a /auth/register (frontend, con el token pre-cargado en la URL de
aceptación) y recién después llama a estos endpoints.

Ubicación en el repo: backend/app/api/v1/endpoints/invitations.py
"""

from fastapi import APIRouter

from app.api.deps.auth import DB, CurrentUser
from app.schemas.common import MessageResponse
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post(
    "/{token}/accept",
    response_model=MessageResponse,
    responses={
        403: {
            "description": "EMAIL_MISMATCH — el email logueado no coincide con el invitado"
        },
        404: {"description": "Invitación no encontrada"},
        409: {"description": "INVITATION_ALREADY_USED"},
        410: {"description": "INVITATION_EXPIRED"},
    },
)
async def accept_invitation(token: str, current_user: CurrentUser, db: DB):
    """Acepta la invitación — agrega al usuario logueado como miembro del
    proyecto con el rol de la invitación."""
    service = InvitationService(db)
    await service.accept_invitation(raw_token=token, current_user=current_user)
    return MessageResponse(
        message="Invitación aceptada — ya eres miembro del proyecto."
    )


@router.post(
    "/{token}/reject",
    response_model=MessageResponse,
    responses={
        403: {
            "description": "EMAIL_MISMATCH — el email logueado no coincide con el invitado"
        },
        404: {"description": "Invitación no encontrada"},
        409: {"description": "INVITATION_ALREADY_USED"},
        410: {"description": "INVITATION_EXPIRED"},
    },
)
async def reject_invitation(token: str, current_user: CurrentUser, db: DB):
    """Rechaza la invitación explícitamente (queda status='rejected')."""
    service = InvitationService(db)
    await service.reject_invitation(raw_token=token, current_user=current_user)
    return MessageResponse(message="Invitación rechazada.")
