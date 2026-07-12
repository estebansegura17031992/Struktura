"""Repository de `project_invitations` — E03 · Sprint 4 · Objetivos 7, 8, 9.

Ubicación en el repo: backend/app/repositories/invitation_repository.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectInvitation


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, invitation_id: UUID) -> ProjectInvitation | None:
        result = await self.session.execute(
            select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> ProjectInvitation | None:
        result = await self.session.execute(
            select(ProjectInvitation).where(ProjectInvitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def count_recent_for_project(
        self, project_id: UUID, *, within_hours: int = 24
    ) -> int:
        """Para el rate limit 10/proyecto/día (Objetivo 7)."""
        cutoff = datetime.now(UTC) - timedelta(hours=within_hours)
        result = await self.session.execute(
            select(func.count(ProjectInvitation.id)).where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.created_at >= cutoff,
            )
        )
        return result.scalar_one()

    async def get_pending_for_email(
        self, project_id: UUID, email: str
    ) -> ProjectInvitation | None:
        """Evita spamear invitaciones duplicadas al mismo email en el mismo
        proyecto mientras haya una pendiente."""
        result = await self.session.execute(
            select(ProjectInvitation).where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.email == email,
                ProjectInvitation.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: UUID,
        email: str,
        role: str,
        token_hash: str,
        invited_by: UUID,
        expires_at: datetime,
    ) -> ProjectInvitation:
        invitation = ProjectInvitation(
            project_id=project_id,
            email=email,
            role=role,
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(invitation)
        await self.session.flush()
        await self.session.refresh(invitation)
        return invitation

    async def set_status(
        self, invitation_id: UUID, status: str, *, responded: bool = False
    ) -> None:
        values: dict = {"status": status}
        if responded:
            values["responded_at"] = datetime.now(UTC)
        await self.session.execute(
            sa_update(ProjectInvitation)
            .where(ProjectInvitation.id == invitation_id)
            .values(**values)
        )

    async def list_expired_pending(self) -> list[ProjectInvitation]:
        """Invitaciones 'pending' cuyo expires_at ya pasó — Objetivo 8 (job)."""
        result = await self.session.execute(
            select(ProjectInvitation).where(
                ProjectInvitation.status == "pending",
                ProjectInvitation.expires_at < datetime.now(UTC),
            )
        )
        return list(result.scalars().all())
