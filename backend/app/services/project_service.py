"""
ProjectService — lógica de negocio
Sprint 2 · E03 · R-0301 a R-0307

Orquesta ProjectRepository, AuditRepository y reglas de negocio.
Los routers no tienen lógica de negocio — solo llaman a este service.
"""
import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = structlog.get_logger(__name__)

# Límite default de proyectos por usuario (owner).
# La fuente de verdad es system_settings.max_projects_per_user.
# Este valor es el fallback si system_settings no tiene la key.
DEFAULT_MAX_PROJECTS = 20


class ProjectService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProjectRepository(db)
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_project_limit(self) -> int:
        """Lee el límite de proyectos desde system_settings. Fallback: DEFAULT_MAX_PROJECTS."""
        try:
            from app.repositories.settings_repository import SettingsRepository  # noqa: PLC0415
            settings = SettingsRepository(self.db)
            value = await settings.get("max_projects_per_user")
            return int(value) if value else DEFAULT_MAX_PROJECTS
        except Exception:
            return DEFAULT_MAX_PROJECTS

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_project(
        self,
        payload: ProjectCreate,
        current_user: User,
    ) -> Project:
        """
        Crea un proyecto y registra al creador como owner.
        Valida límite de proyectos antes de crear (R-0301).
        Operación atómica: proyecto + membresía owner en la misma transacción.
        """
        # Validar que solo editor/admin puede crear proyectos
        if current_user.role not in ("editor", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Solo editores y admins pueden crear proyectos.",
                    }
                },
            )

        # Validar límite de proyectos como owner (R-0301)
        max_projects = await self._get_project_limit()
        owned_count = await self.repo.count_owned_active(current_user.id)
        if owned_count >= max_projects:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "PROJECT_LIMIT_REACHED",
                        "message": (
                            f"Has alcanzado el límite de {max_projects} proyectos como owner. "
                            "Elimina un proyecto existente o contacta al administrador."
                        ),
                        "details": {"limit": max_projects, "current": owned_count},
                    }
                },
            )

        # Crear proyecto y membresía owner en la misma transacción
        project = await self.repo.create(
            name=payload.name,
            owner_id=current_user.id,
            description=payload.description,
        )
        await self.repo.add_member(
            project_id=project.id,
            user_id=current_user.id,
            role=ProjectMemberRole.owner,
        )

        await self.db.commit()
        await self.db.refresh(project)

        logger.info(
            "project.created",
            project_id=str(project.id),
            owner_id=str(current_user.id),
        )
        return project

    async def list_projects(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        """Lista proyectos donde el usuario es miembro activo."""
        page_size = min(page_size, 100)
        return await self.repo.list_by_user(current_user.id, page, page_size)

    async def update_project(
        self,
        project_id: uuid.UUID,
        payload: ProjectUpdate,
        current_user: User,
        membership: ProjectMember,
    ) -> Project:
        """
        Actualiza nombre/descripción del proyecto.
        Solo owner o admin del sistema puede editar (R-0301).
        """
        project = await self.repo.get_active_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"error": {"code": "NOT_FOUND", "message": "Proyecto no encontrado."}})

        # Solo owner de proyecto o admin del sistema puede editar
        if membership.role != ProjectMemberRole.owner and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Solo el owner o un admin puede editar este proyecto."}},
            )

        updated = await self.repo.update(
            project,
            name=payload.name,
            description=payload.description,
        )
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def delete_project(
        self,
        project_id: uuid.UUID,
        current_user: User,
        membership: ProjectMember,
    ) -> None:
        """
        Soft delete del proyecto (R-0302).
        Rechaza con 409 si tiene tareas activas — lista las primeras 10 tareas bloqueantes.
        Solo owner o admin puede eliminar.
        """
        project = await self.repo.get_active_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"error": {"code": "NOT_FOUND", "message": "Proyecto no encontrado."}})

        if membership.role != ProjectMemberRole.owner and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Solo el owner o un admin puede eliminar este proyecto."}},
            )

        # Validar tareas activas antes de eliminar (R-0302 — decisión cerrada en kick-off)
        blocking_tasks = await self.repo.get_active_task_names(project_id)
        if blocking_tasks:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "PROJECT_HAS_ACTIVE_TASKS",
                        "message": (
                            "No se puede eliminar el proyecto porque tiene tareas activas. "
                            "Completa o elimina las tareas antes de continuar."
                        ),
                        "details": {
                            "blocking_tasks": blocking_tasks,
                            "note": "Se muestran hasta 10 tareas bloqueantes.",
                        },
                    }
                },
            )

        await self.repo.soft_delete(project)
        await self.audit.log(
            db=self.db,
            actor_id=current_user.id,
            action="project_deleted",
            entity_type="project",
            entity_id=project_id,
            metadata={"project_name": project.name},
        )
        await self.db.commit()
        logger.info("project.deleted", project_id=str(project_id), actor_id=str(current_user.id))

    # ── Membresía ─────────────────────────────────────────────────────────────

    async def add_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: ProjectMemberRole,
        current_user: User,
        membership: ProjectMember,
    ) -> ProjectMember:
        """
        Agrega un miembro al proyecto (R-0303).
        Solo owner o editor del proyecto puede agregar miembros.

        Seguridad: un editor no puede agregar a alguien con rol owner.
        Esto previene escalada de privilegios (riesgo identificado en kick-off).
        """
        # Validar rol del actor
        if membership.role == ProjectMemberRole.viewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Los viewers no pueden gestionar miembros."}},
            )

        # Prevenir escalada: un editor no puede asignar rol owner
        if (
            membership.role == ProjectMemberRole.editor
            and role == ProjectMemberRole.owner
            and current_user.role != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Solo el owner o un admin puede asignar el rol de owner.",
                    }
                },
            )

        # Verificar que el usuario a agregar existe
        target_user = await self.users.get_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "Usuario no encontrado."}},
            )

        # Verificar si ya tiene membresía activa
        existing = await self.repo.get_active_membership(project_id, user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "MEMBER_ALREADY_EXISTS", "message": "El usuario ya es miembro activo del proyecto."}},
            )

        new_member = await self.repo.add_member(project_id, user_id, role)
        await self.db.commit()
        await self.db.refresh(new_member)
        return new_member

    async def remove_member(
        self,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        current_user: User,
        membership: ProjectMember,
    ) -> ProjectMember:
        """
        Soft delete de membresía (R-0303).
        El owner no puede ser removido — debe transferir ownership primero.
        """
        if membership.role == ProjectMemberRole.viewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Los viewers no pueden gestionar miembros."}},
            )

        target_membership = await self.repo.get_active_membership(project_id, target_user_id)
        if not target_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "El usuario no es miembro activo del proyecto."}},
            )

        # No se puede remover al owner directamente
        if target_membership.role == ProjectMemberRole.owner:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "CANNOT_REMOVE_OWNER",
                        "message": "No se puede remover al owner del proyecto. Transfiere el ownership primero.",
                    }
                },
            )

        removed = await self.repo.remove_member(target_membership)
        await self.db.commit()
        return removed

    async def transfer_ownership(
        self,
        project_id: uuid.UUID,
        new_owner_id: uuid.UUID,
        current_user: User,
        membership: ProjectMember,
    ) -> tuple[ProjectMember, ProjectMember]:
        """
        Transferencia atómica de ownership (DU-02 · R-0304).
        Solo el owner actual puede transferir.
        El nuevo owner debe ser miembro activo del proyecto.
        Registra en audit_logs con action='ownership_transferred'.
        """
        # Solo el owner puede transferir
        if membership.role != ProjectMemberRole.owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Solo el owner puede transferir el ownership."}},
            )

        # No puede transferirse a sí mismo
        if new_owner_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "INVALID_OPERATION", "message": "No puedes transferir el ownership a ti mismo."}},
            )

        # El nuevo owner debe ser miembro activo
        new_owner_membership = await self.repo.get_active_membership(project_id, new_owner_id)
        if not new_owner_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "El nuevo owner debe ser miembro activo del proyecto."}},
            )

        project = await self.repo.get_active_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"error": {"code": "NOT_FOUND", "message": "Proyecto no encontrado."}})

        # Operación atómica
        prev_owner, new_owner = await self.repo.transfer_ownership(
            project=project,
            current_owner_membership=membership,
            new_owner_membership=new_owner_membership,
        )

        # Audit log (R-0304 + ART-18)
        await self.audit.log(
            db=self.db,
            actor_id=current_user.id,
            action="ownership_transferred",
            entity_type="project",
            entity_id=project_id,
            metadata={
                "previous_owner_id": str(current_user.id),
                "new_owner_id": str(new_owner_id),
                "project_name": project.name,
            },
        )

        await self.db.commit()

        logger.info(
            "project.ownership_transferred",
            project_id=str(project_id),
            from_user=str(current_user.id),
            to_user=str(new_owner_id),
        )
        return prev_owner, new_owner

    async def get_member_history(
        self,
        project_id: uuid.UUID,
        current_user: User,
        membership: ProjectMember,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProjectMember], int]:
        """
        Historial de membresías (activas + removidas).
        Solo accesible para owner o admin del sistema (R-0306).
        """
        if membership.role not in (ProjectMemberRole.owner, ProjectMemberRole.editor) \
                and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Solo el owner o un admin puede ver el historial de miembros."}},
            )

        return await self.repo.list_member_history(project_id, page, min(page_size, 100))