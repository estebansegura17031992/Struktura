"""
Dependencies FastAPI — RBAC y membresía de proyecto
Sprint 2 · E02 · ART-01 (require_role) · ART-02 (verify_project_membership)

Patrón de uso en routers:

    @router.get("/projects/{project_id}/members")
    async def list_members(
        project_id: UUID,
        current_user: User = Depends(get_current_user),
        _: None = Depends(require_role("admin", "editor")),
        _member: ProjectMember = Depends(verify_project_membership),
    ):
        ...
"""

import uuid
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.db import get_db
from app.models.project import ProjectMember
from app.models.user import User

logger = structlog.get_logger(__name__)


# ── require_role ───────────────────────────────────────────────────────────────


def require_role(*allowed_roles: str):
    """
    Dependency factory que valida el rol global del usuario (users.role).
    El JWT contiene únicamente el rol global; el rol de proyecto se consulta en DB.

    Uso:
        Depends(require_role("admin"))
        Depends(require_role("admin", "editor"))

    Retorna 403 FORBIDDEN con código descriptivo ante violación.
    No retorna 401 — si llegamos aquí, el token ya fue validado por get_current_user.

    ART-01 · R-0201 · R-0202
    """

    async def _check_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "rbac.access_denied",
                user_id=str(current_user.id),
                user_role=current_user.role,
                required_roles=allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": (
                            f"Se requiere rol {' o '.join(allowed_roles)} "
                            f"para esta operación. Tu rol actual es '{current_user.role}'."
                        ),
                        "details": {
                            "your_role": current_user.role,
                            "required_roles": list(allowed_roles),
                        },
                    }
                },
            )
        return current_user

    return _check_role


# ── verify_project_membership ──────────────────────────────────────────────────


async def verify_project_membership(
    project_id: Annotated[uuid.UUID, Path(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectMember:
    """
    Valida que el usuario tiene membresía activa (removed_at IS NULL) en el proyecto.
    Se inyecta en endpoints que operan sobre recursos de un proyecto específico.

    - Retorna 403 si el usuario no es miembro activo (no 404, para no revelar existencia).
    - Retorna 404 si el proyecto no existe o está soft-deleted.
    - Retorna el ProjectMember para que el router pueda acceder al rol del proyecto.

    El rol de proyecto (owner|editor|viewer) es independiente del rol global.
    Regla de precedencia: se aplica el más restrictivo entre sistema y proyecto.

    ART-02 · R-0202
    """
    from app.repositories.project_repository import ProjectRepository

    repo = ProjectRepository(db)

    # Verificar que el proyecto existe y no está soft-deleted
    project = await repo.get_by_id(project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Proyecto no encontrado.",
                }
            },
        )

    # Los admins del sistema tienen acceso a todos los proyectos
    # sin necesidad de membresía explícita (R-0202)
    if current_user.role == "admin":
        membership = await repo.get_active_membership(project_id, current_user.id)
        if membership:
            return membership
        # Admin sin membresía: crear un ProjectMember virtual con rol editor
        # para no bloquear operaciones administrativas
        virtual_member = ProjectMember()
        virtual_member.project_id = project_id
        virtual_member.user_id = current_user.id
        virtual_member.role = "editor"
        virtual_member.removed_at = None
        return virtual_member

    # Verificar membresía activa para roles no-admin
    membership = await repo.get_active_membership(project_id, current_user.id)
    if not membership:
        logger.warning(
            "project.access_denied",
            user_id=str(current_user.id),
            project_id=str(project_id),
            user_role=current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "No tienes membresía activa en este proyecto.",
                }
            },
        )

    return membership


# ── Helpers de autorización de proyecto ───────────────────────────────────────


def require_project_role(*allowed_project_roles: str):
    """
    Dependency factory que valida el rol dentro del proyecto.
    Se usa DESPUÉS de verify_project_membership.

    Uso:
        membership: ProjectMember = Depends(verify_project_membership),
        _: None = Depends(require_project_role("owner")),

    Roles válidos: owner | editor | viewer
    R-0202
    """

    async def _check_project_role(
        membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    ) -> ProjectMember:
        if membership.role not in allowed_project_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": (
                            f"Se requiere rol de proyecto "
                            f"{' o '.join(allowed_project_roles)} "
                            f"para esta operación."
                        ),
                        "details": {
                            "your_project_role": membership.role,
                            "required_project_roles": list(allowed_project_roles),
                        },
                    }
                },
            )
        return membership

    return _check_project_role
