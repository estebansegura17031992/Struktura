"""
ProjectRepository — capa de acceso a datos
Sprint 2 · E03 · R-0301 a R-0307

Solo queries SQLAlchemy. Sin lógica de negocio.
La lógica de negocio vive en ProjectService.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectMemberRole


class ProjectRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Project ───────────────────────────────────────────────────────────────

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Obtiene proyecto por ID (incluye soft-deleted para validaciones internas)."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Obtiene proyecto activo por ID. Excluye soft-deleted."""
        result = await self.db.execute(
            select(Project).where(
                and_(Project.id == project_id, Project.deleted_at.is_(None))
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
        Retorna (items, total) para paginación.
        """
        base_query = (
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

        total_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar_one()

        paginated = await self.db.execute(
            base_query.offset((page - 1) * page_size).limit(page_size)
        )
        items = list(paginated.scalars().all())

        return items, total

    async def count_owned_active(self, user_id: uuid.UUID) -> int:
        """
        Cuenta proyectos activos donde el usuario es owner.
        Usado para validar límite de system_settings.max_projects_per_user.
        Solo cuenta proyectos como owner, no como miembro (R-0301).
        """
        result = await self.db.execute(
            select(func.count()).where(
                and_(
                    Project.owner_id == user_id,
                    Project.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one()

    async def create(
        self,
        name: str,
        owner_id: uuid.UUID,
        description: str | None = None,
    ) -> Project:
        """Crea proyecto. El ProjectService crea la membresía owner en la misma transacción."""
        project = Project(
            name=name,
            description=description,
            owner_id=owner_id,
        )
        self.db.add(project)
        await self.db.flush()  # Para obtener el ID antes del commit
        return project

    async def update(
        self,
        project: Project,
        name: str | None = None,
        description: str | None = None,
    ) -> Project:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        await self.db.flush()
        return project

    async def soft_delete(self, project: Project) -> Project:
        """
        Soft delete del proyecto (R-0302).
        La validación de tareas activas se hace en ProjectService antes de llamar esto.
        """
        project.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return project

    async def has_active_tasks(self, project_id: uuid.UUID) -> bool:
        """
        Verifica si el proyecto tiene tareas activas (status != 'completo' AND deleted_at IS NULL).
        Usado por ProjectService para validar soft-delete (R-0302).
        """
        # Importación inline para evitar circular imports con Task model (E04)
        from app.models.task import Task  # noqa: PLC0415

        result = await self.db.execute(
            select(func.count()).where(
                and_(
                    Task.project_id == project_id,
                    Task.status != "completo",
                    Task.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one() > 0

    async def get_active_task_names(self, project_id: uuid.UUID) -> list[str]:
        """
        Retorna nombres de tareas activas bloqueantes para el soft-delete (R-0302).
        Máximo 10 nombres para el mensaje de error (no desbordar el response).
        """
        from app.models.task import Task  # noqa: PLC0415

        result = await self.db.execute(
            select(Task.name).where(
                and_(
                    Task.project_id == project_id,
                    Task.status != "completo",
                    Task.deleted_at.is_(None),
                )
            ).limit(10)
        )
        return list(result.scalars().all())

    # ── ProjectMember ─────────────────────────────────────────────────────────

    async def get_active_membership(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ProjectMember | None:
        """
        Obtiene membresía activa de un usuario en un proyecto.
        Usado por verify_project_membership dependency.
        El índice parcial ix_project_members_active hace esta query O(log n).
        """
        result = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.removed_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_active_members(
        self,
        project_id: uuid.UUID,
    ) -> list[ProjectMember]:
        """Lista miembros activos de un proyecto con datos del usuario cargados."""
        result = await self.db.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.removed_at.is_(None),
                )
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
        """
        Historial completo de membresías (activas + removidas).
        Solo accesible para owner/admin (R-0306). La validación de rol es en ProjectService.
        """
        base_query = (
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.desc())
        )

        total_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar_one()

        paginated = await self.db.execute(
            base_query.offset((page - 1) * page_size).limit(page_size)
        )
        return list(paginated.scalars().all()), total

    async def add_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: ProjectMemberRole,
    ) -> ProjectMember:
        """Agrega un miembro al proyecto. El service valida unicidad activa antes."""
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def remove_member(self, membership: ProjectMember) -> ProjectMember:
        """
        Soft delete de membresía: establece removed_at (R-0303).
        El registro histórico se conserva con joined_at y removed_at.
        """
        membership.removed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return membership

    async def get_owner_membership(self, project_id: uuid.UUID) -> ProjectMember | None:
        """Obtiene la membresía del owner actual. Usado en transferencia de ownership."""
        result = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.role == ProjectMemberRole.owner,
                    ProjectMember.removed_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def transfer_ownership(
        self,
        project: Project,
        current_owner_membership: ProjectMember,
        new_owner_membership: ProjectMember,
    ) -> tuple[ProjectMember, ProjectMember]:
        """
        Transferencia atómica de ownership (DU-02 · R-0304).
        El owner actual queda como editor. El nuevo owner queda como owner.
        Ambos cambios en la misma operación — el commit es responsabilidad del service.
        """
        current_owner_membership.role = ProjectMemberRole.editor
        new_owner_membership.role = ProjectMemberRole.owner
        project.owner_id = new_owner_membership.user_id
        await self.db.flush()
        return current_owner_membership, new_owner_membership