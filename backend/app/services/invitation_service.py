"""Service de invitaciones a proyecto — E03 · Sprint 4 · Objetivos 7, 8, 9.

Sin lógica de RBAC de "quién puede llamar este endpoint" salvo la regla de
negocio específica (solo owner/admin invita/cancela) — mismo patrón que
TaskService/ProjectService: el chequeo de membresía en sí vive en el
endpoint (ProjectMembership).

Ubicación en el repo: backend/app/services/invitation_service.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppBaseError, InsufficientPermissionsError
from app.core.security import generate_opaque_token, hash_token
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.invitation import InvitationOut
from app.services.audit_service import log_action
from app.services.email_service import send_project_invitation_email

DEFAULT_INVITATION_EXPIRY_DAYS = 7
MAX_INVITATIONS_PER_DAY = 10


async def _get_invitation_expiry_days(session: AsyncSession) -> int:
    """Lee system_settings.invitation_expiry_days (sembrada en 0001, =7)."""
    result = await session.execute(
        text("SELECT value FROM system_settings WHERE key = 'invitation_expiry_days'")
    )
    row = result.first()
    if row is None:
        return DEFAULT_INVITATION_EXPIRY_DAYS
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return DEFAULT_INVITATION_EXPIRY_DAYS


class InvitationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InvitationRepository(session)
        self._project_repo = ProjectRepository(session)
        self._user_repo = UserRepository(session)

    # ── Objetivo 7 ───────────────────────────────────────────────────────

    async def create_invitation(
        self,
        *,
        project_id: UUID,
        email: str,
        role: str,
        actor: User,
        membership: ProjectMember,
    ) -> InvitationOut:
        """Solo owner del proyecto (o admin del sistema) invita. El rol ya
        viene limitado a viewer/editor por el schema (InvitationCreate) y
        por el CHECK CONSTRAINT pi_role_not_owner en DB — doble defensa."""
        if membership.role != "owner" and actor.role != "admin":
            raise InsufficientPermissionsError()

        recent_count = await self._repo.count_recent_for_project(project_id)
        if recent_count >= MAX_INVITATIONS_PER_DAY:
            raise AppBaseError(
                "INVITATION_RATE_LIMIT_EXCEEDED",
                f"Se alcanzó el límite de {MAX_INVITATIONS_PER_DAY} "
                f"invitaciones por día para este proyecto.",
                429,
            )

        existing_pending = await self._repo.get_pending_for_email(project_id, email)
        if existing_pending is not None:
            raise AppBaseError(
                "INVITATION_ALREADY_PENDING",
                "Ya existe una invitación pendiente para este email en este proyecto.",
                409,
            )

        target_user = await self._user_repo.get_by_email(email)
        if target_user is not None:
            active_membership = await self._project_repo.get_active_membership(
                project_id, target_user.id
            )
            if active_membership is not None:
                raise AppBaseError(
                    "MEMBER_ALREADY_EXISTS",
                    "Este usuario ya es miembro activo del proyecto.",
                    409,
                )

        raw_token = generate_opaque_token()
        token_hash = hash_token(raw_token)
        expiry_days = await _get_invitation_expiry_days(self._session)
        expires_at = datetime.now(UTC) + timedelta(days=expiry_days)

        invitation = await self._repo.create(
            project_id=project_id,
            email=email,
            role=role,
            token_hash=token_hash,
            invited_by=actor.id,
            expires_at=expires_at,
        )

        await log_action(
            self._session,
            action="invitation_created",
            user_id=actor.id,
            entity_type="project_invitation",
            entity_id=invitation.id,
            metadata={"project_id": str(project_id), "email": email, "role": role},
        )
        await self._session.commit()

        project = await self._project_repo.get_active(project_id)
        accept_url = f"{settings.FRONTEND_URL}/invitations/accept?token={raw_token}"
        await send_project_invitation_email(
            email,
            project.name if project else "Struktura",
            actor.username,
            accept_url,
        )

        return InvitationOut.model_validate(invitation)

    async def list_invitations(
        self,
        *,
        project_id: UUID,
        actor: User,
        membership: ProjectMember,
    ) -> list[InvitationOut]:
        """Solo owner/admin puede ver la lista — mismo gate que crear/cancelar
        (Frontend Sprint 4 · Objetivo 6, endpoint agregado junto con la UI
        porque el backend no lo había expuesto)."""
        if membership.role != "owner" and actor.role != "admin":
            raise InsufficientPermissionsError()

        invitations = await self._repo.list_for_project(project_id)
        return [InvitationOut.model_validate(i) for i in invitations]

    # ── Objetivo 8 ───────────────────────────────────────────────────────

    async def _resolve_pending(self, raw_token: str):
        token_hash = hash_token(raw_token)
        invitation = await self._repo.get_by_token_hash(token_hash)
        if invitation is None:
            raise AppBaseError("NOT_FOUND", "Invitación no encontrada.", 404)
        if invitation.status != "pending":
            raise AppBaseError(
                "INVITATION_ALREADY_USED", "Esta invitación ya fue utilizada.", 409
            )
        if invitation.expires_at < datetime.now(UTC):
            await self._repo.set_status(invitation.id, "expired")
            await self._session.commit()
            raise AppBaseError("INVITATION_EXPIRED", "Esta invitación expiró.", 410)
        return invitation

    async def accept_invitation(self, *, raw_token: str, current_user: User) -> None:
        invitation = await self._resolve_pending(raw_token)

        if current_user.email.lower() != invitation.email.lower():
            raise AppBaseError(
                "EMAIL_MISMATCH", "Esta invitación fue enviada a otro email.", 403
            )

        existing = await self._project_repo.get_active_membership(
            invitation.project_id, current_user.id
        )
        if existing is None:
            new_member = ProjectMember(
                project_id=invitation.project_id,
                user_id=current_user.id,
                role=invitation.role,
                invited_by=invitation.invited_by,
            )
            self._session.add(new_member)

        await self._repo.set_status(invitation.id, "accepted", responded=True)
        await log_action(
            self._session,
            action="invitation_accepted",
            user_id=current_user.id,
            entity_type="project_invitation",
            entity_id=invitation.id,
            metadata={
                "project_id": str(invitation.project_id),
                "role": invitation.role,
            },
        )
        await self._session.commit()

    async def reject_invitation(self, *, raw_token: str, current_user: User) -> None:
        invitation = await self._resolve_pending(raw_token)

        if current_user.email.lower() != invitation.email.lower():
            raise AppBaseError(
                "EMAIL_MISMATCH", "Esta invitación fue enviada a otro email.", 403
            )

        await self._repo.set_status(invitation.id, "rejected", responded=True)
        await log_action(
            self._session,
            action="invitation_rejected",
            user_id=current_user.id,
            entity_type="project_invitation",
            entity_id=invitation.id,
            metadata={"project_id": str(invitation.project_id)},
        )
        await self._session.commit()

    async def close_expired_invitations(self) -> int:
        """Job periódico — marca 'expired' las pending vencidas (Objetivo 8)."""
        expired = await self._repo.list_expired_pending()
        for invitation in expired:
            await self._repo.set_status(invitation.id, "expired")
        if expired:
            await self._session.commit()
        return len(expired)

    # ── Objetivo 9 ───────────────────────────────────────────────────────

    async def cancel_invitation(
        self,
        *,
        project_id: UUID,
        invitation_id: UUID,
        actor: User,
        membership: ProjectMember,
    ) -> None:
        """Solo owner/admin cancela. La invitación queda 'expired' (no se
        borra el registro — trazabilidad)."""
        if membership.role != "owner" and actor.role != "admin":
            raise InsufficientPermissionsError()

        invitation = await self._repo.get_by_id(invitation_id)
        if invitation is None or invitation.project_id != project_id:
            raise AppBaseError("NOT_FOUND", "Invitación no encontrada.", 404)
        if invitation.status != "pending":
            raise AppBaseError(
                "INVITATION_ALREADY_USED",
                "Solo se pueden cancelar invitaciones pendientes.",
                409,
            )

        await self._repo.set_status(invitation.id, "expired")
        await log_action(
            self._session,
            action="invitation_cancelled",
            user_id=actor.id,
            entity_type="project_invitation",
            entity_id=invitation.id,
            metadata={"project_id": str(project_id)},
        )
        await self._session.commit()
