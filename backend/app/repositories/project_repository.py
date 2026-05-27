"""
ProjectRepository — queries de DB para proyectos y membresías.
Sin lógica de negocio — solo acceso a datos.
Sprint 2 · E03 · R-0301 a R-0307
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.models.project import Project, ProjectMember
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession):
        super().__init__(Project, session)

    # ── Project ───────────────────────────────────────────────────────────────

    async def get_active(self, project_id: uuid.UUID) -> Project | None:
        """Obtiene proyecto activo (no soft-deleted)."""
        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        """
        Lista proyectos donde el usuario es miembro activo.
        Retorna (items, total) para el wrapper de paginación estándar.
        """
        base_q = (
            select(Project)
            .join(
                ProjectMember,
                and_(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.removed_at.is_(None),
                ),
            )
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
        )
        total_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total = total_result.scalar_one()

        result = await self.session.execute(
            base_q.offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def count_owned_active(self, owner_id: uuid.UUID) -> int:
        """Cuenta proyectos activos donde el usuario es owner (para validar límite)."""
        result = await self.session.execute(
            select(func.count()).where(
                Project.owner_id == owner_id,
                Project.deleted_at.is_(None),
            )
        )
        return result.scalar_one()

    async def get_active_task_names(
        self, project_id: uuid.UUID, limit: int = 10
    ) -> list[str]:
        """
        Retorna nombres de tareas activas (status != completo, no deleted).
        Usado para el mensaje de error 409 en soft-delete.
        Importación lazy del modelo Task para evitar circular imports (E04 aún no existe).
        """
        try:
            from app.models.task import Task  # noqa: PLC0415
            result = await self.session.execute(
                select(Task.title).where(
                    and_(
                        Task.project_id == project_id,
                        Task.status != "completo",
                        Task.deleted_at.is_(None),
                    )
                ).limit(limit)
            )
            return list(result.scalars().all())
        except ImportError:
            # Task model no existe todavía (Sprint 3) — no hay tareas activas
            return []

    # ── ProjectMember ─────────────────────────────────────────────────────────

    async def get_active_membership(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ProjectMember | None:
        """
        Membresía activa (removed_at IS NULL).
        El índice parcial ix_project_members_active hace esta query O(log n).
        """
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.removed_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_active_members(
        self, project_id: uuid.UUID
    ) -> list[ProjectMember]:
        result = await self.session.execute(
            select(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.removed_at.is_(None),
            )
            .order_by(ProjectMember.joined_at.asc())
        )
        return list(result.scalars().all())

    async def list_member_history(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProjectMember], int]:
        """Historial completo — activos e históricos."""
        base_q = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.desc())
        )
        total_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total = total_result.scalar_one()
        result = await self.session.execute(
            base_q.offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_owner_membership(
        self, project_id: uuid.UUID
    ) -> ProjectMember | None:
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == "owner",
                ProjectMember.removed_at.is_(None),
            )
        )
        return result.scalar_one_or_none()