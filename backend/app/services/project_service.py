"""
ProjectService — lógica de negocio de proyectos y membresía.
Orquesta ProjectRepository y audit_service.
Sprint 2 · E03 · R-0301 a R-0307
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppBaseError,
    InsufficientPermissionsError,
    UserNotFoundError,
)
from app.core.logging import get_logger
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import log_action

logger = get_logger(__name__)

DEFAULT_MAX_PROJECTS = 20


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProjectRepository(session)
        self.user_repo = UserRepository(session)

    async def _get_project_limit(self) -> int:
        """Lee límite desde system_settings. Fallback: DEFAULT_MAX_PROJECTS."""
        try:
            from app.models.auth import SystemSetting  # noqa: PLC0415

            result = await self.session.execute(
                select(SystemSetting).where(
                    SystemSetting.key == "max_projects_per_user"
                )
            )
            setting = result.scalar_one_or_none()
            return int(setting.value) if setting else DEFAULT_MAX_PROJECTS
        except Exception:
            return DEFAULT_MAX_PROJECTS

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(
        self,
        name: str,
        description: str | None,
        current_user: User,
    ) -> Project:
        """
        Crea proyecto y registra al creador como owner en project_members.
        Solo editors y admins pueden crear. Valida límite de proyectos.
        Operación atómica: proyecto + membresía en la misma transacción.
        R-0301
        """
        if current_user.role not in ("editor", "admin"):
            raise InsufficientPermissionsError()

        max_projects = await self._get_project_limit()
        owned = await self.repo.count_owned_active(current_user.id)
        if owned >= max_projects:
            raise AppBaseError(
                "PROJECT_LIMIT_REACHED",
                f"Has alcanzado el límite de {max_projects} proyectos como owner.",
                422,
            )

        project = await self.repo.create(
            name=name.strip(),
            description=description,
            owner_id=current_user.id,
        )

        # Registrar al creador como owner
        owner_member = ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role="owner",
            invited_by=None,
        )
        self.session.add(owner_member)
        await self.session.flush()

        await self.session.commit()
        await self.session.refresh(project)

        logger.info(
            "project_created", project_id=str(project.id), owner=str(current_user.id)
        )
        return project

    async def soft_delete(self, project_id: uuid.UUID, current_user: User) -> None:
        """
        Soft delete con validación de tareas activas.
        Rechaza con 409 y lista hasta 10 tareas bloqueantes.
        R-0302 — decisión cerrada en kick-off: rechazar, no archivar.
        """
        project = await self.repo.get_active(project_id)
        if not project:
            raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

        blocking = await self.repo.get_active_task_names(project_id)
        if blocking:
            raise AppBaseError(
                "PROJECT_HAS_ACTIVE_TASKS",
                "No se puede eliminar el proyecto porque tiene tareas activas. "
                "Completa o elimina las tareas antes de continuar.",
                409,
            )

        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(deleted_at=datetime.now(UTC))
        )

        await log_action(
            self.session,
            "project_deleted",
            user_id=current_user.id,
            entity_type="project",
            entity_id=project_id,
            metadata={"project_name": project.name},
        )
        await self.session.commit()
        logger.info(
            "project_deleted", project_id=str(project_id), actor=str(current_user.id)
        )

    # ── Membresía ─────────────────────────────────────────────────────────────

    async def add_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        current_user: User,
        membership: ProjectMember,
    ) -> ProjectMember:
        """
        Agrega miembro al proyecto.
        Previene escalada de privilegios: editor no puede asignar rol owner.
        R-0303
        """
        if membership.role == "viewer":
            raise InsufficientPermissionsError()

        # Prevenir escalada: editor no puede asignar owner
        if (
            membership.role == "editor"
            and role == "owner"
            and current_user.role != "admin"
        ):
            raise AppBaseError(
                "FORBIDDEN",
                "Solo el owner o un admin puede asignar el rol de owner.",
                403,
            )

        # Verificar que el usuario a agregar existe
        target = await self.user_repo.get_by_id(user_id)
        if not target:
            raise UserNotFoundError()

        # Verificar membresía activa duplicada
        existing = await self.repo.get_active_membership(project_id, user_id)
        if existing:
            raise AppBaseError(
                "MEMBER_ALREADY_EXISTS",
                "El usuario ya es miembro activo del proyecto.",
                409,
            )

        new_member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
            invited_by=current_user.id,
        )
        self.session.add(new_member)
        await self.session.flush()

        # Refrescar para obtener el objeto completo
        result = await self.repo.get_active_membership(project_id, user_id)

        await log_action(
            self.session,
            "member_added",
            user_id=current_user.id,
            entity_type="project",
            entity_id=project_id,
            metadata={
                "added_user_id": str(user_id),
                "role": role,
            },
        )
        await self.session.commit()
        if result is None:
            raise AppBaseError("INTERNAL_ERROR", "Error al agregar el miembro.", 500)
        logger.info(
            "member_added",
            project_id=str(project_id),
            user_id=str(user_id),
            role=role,
            actor=str(current_user.id),
        )
        return result

    async def remove_member(
        self,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        current_user: User,
        membership: ProjectMember,
    ) -> None:
        """
        Soft delete de membresía: establece removed_at.
        El owner no puede ser removido directamente.
        R-0303
        """
        if membership.role == "viewer":
            raise InsufficientPermissionsError()

        target_membership = await self.repo.get_active_membership(
            project_id, target_user_id
        )
        if not target_membership:
            raise AppBaseError("NOT_FOUND", "El usuario no es miembro activo.", 404)

        if target_membership.role == "owner":
            raise AppBaseError(
                "CANNOT_REMOVE_OWNER",
                "No se puede remover al owner. Transfiere el ownership primero.",
                409,
            )

        await self.session.execute(
            update(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == target_user_id,
                ProjectMember.removed_at.is_(None),
            )
            .values(removed_at=datetime.now(UTC))
        )

        await log_action(
            self.session,
            "member_removed",
            user_id=current_user.id,
            entity_type="project",
            entity_id=project_id,
            metadata={
                "removed_user_id": str(target_user_id),
                "previous_role": target_membership.role,
            },
        )
        await self.session.commit()
        logger.info(
            "member_removed",
            project_id=str(project_id),
            target_user_id=str(target_user_id),
            actor=str(current_user.id),
        )

    async def transfer_ownership(
        self,
        project_id: uuid.UUID,
        new_owner_id: uuid.UUID,
        current_user: User,
        membership: ProjectMember,
    ) -> None:
        """
        Transferencia atómica de ownership.
        Solo el owner actual puede transferir.
        El nuevo owner debe ser miembro activo.
        Registra en audit_logs. DU-02 · R-0304
        """
        if membership.role != "owner":
            raise InsufficientPermissionsError()

        if new_owner_id == current_user.id:
            raise AppBaseError(
                "INVALID_OPERATION",
                "No puedes transferirte el ownership a ti mismo.",
                409,
            )

        new_owner_membership = await self.repo.get_active_membership(
            project_id, new_owner_id
        )
        if not new_owner_membership:
            raise AppBaseError(
                "NOT_FOUND",
                "El nuevo owner debe ser miembro activo del proyecto.",
                404,
            )

        project = await self.repo.get_active(project_id)
        if not project:
            raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

        # Operación atómica: cambiar ambos roles y el owner_id del proyecto
        await self.session.execute(
            update(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
                ProjectMember.removed_at.is_(None),
            )
            .values(role="editor")
        )
        await self.session.execute(
            update(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == new_owner_id,
                ProjectMember.removed_at.is_(None),
            )
            .values(role="owner")
        )
        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(owner_id=new_owner_id)
        )

        await log_action(
            self.session,
            "ownership_transferred",
            user_id=current_user.id,
            entity_type="project",
            entity_id=project_id,
            metadata={
                "previous_owner_id": str(current_user.id),
                "new_owner_id": str(new_owner_id),
                "project_name": project.name,
            },
        )
        await self.session.commit()
        logger.info(
            "ownership_transferred",
            project_id=str(project_id),
            from_user=str(current_user.id),
            to_user=str(new_owner_id),
        )
