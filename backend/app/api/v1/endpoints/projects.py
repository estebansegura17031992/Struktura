"""
Endpoints de gestión de proyectos y membresía (E03 · R-0301 a R-0307).
Todos los endpoints de proyecto requieren membresía activa o rol admin,
validado mediante get_project_member() dependency.
Endpoints:
  POST   /projects                              – crear proyecto
  GET    /projects                              – listar proyectos del usuario
  PATCH  /projects/{project_id}                 – editar proyecto
  DELETE /projects/{project_id}                 – soft delete
  GET    /projects/{project_id}/members         – listar miembros activos
  POST   /projects/{project_id}/members         – agregar miembro
  DELETE /projects/{project_id}/members/{uid}   – remover miembro
  GET    /projects/{project_id}/members/history – historial de membresías
  POST   /projects/{project_id}/transfer-ownership – transferir ownership
"""

import math
from datetime import UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import DB, CurrentUser, get_current_user
from app.api.deps.db import get_db
from app.core.exceptions import (
    AppBaseError,
    InsufficientPermissionsError,
)
from app.core.logging import get_logger
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.invitation import InvitationCreate, InvitationOut
from app.services.invitation_service import InvitationService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger(__name__)


# ── Schemas inline ─────────────────────────────────────────────────────────────


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Rediseño UI Alpha",
                "description": "Optimización del sistema de diseño core",
            }
        }
    }

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar en blanco")
        return v.strip()


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Rediseño UI Alpha v2",
                "description": "Descripción actualizada",
            }
        }
    }


class AddMemberRequest(BaseModel):
    user_id: UUID
    role: str = "viewer"

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "editor",
            }
        }
    }

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"owner", "editor", "viewer"}:
            raise ValueError("Rol inválido. Permitidos: owner, editor, viewer")
        return v


class TransferOwnershipRequest(BaseModel):
    new_owner_id: UUID

    model_config = {
        "json_schema_extra": {
            "example": {"new_owner_id": "550e8400-e29b-41d4-a716-446655440000"}
        }
    }


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: str
    updated_at: str
    my_role: str | None = None  # rol del usuario autenticado en este proyecto
    member_count: int | None = None  # calculado en list_projects

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(
        cls,
        p: Project,
        my_role: str | None = None,
        member_count: int | None = None,
    ) -> "ProjectResponse":
        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            owner_id=p.owner_id,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            my_role=my_role,
            member_count=member_count,
        )


class MemberUserInfo(BaseModel):
    id: str
    username: str
    full_name: str | None


class MemberResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    role: str
    joined_at: str
    removed_at: str | None
    is_active: bool
    user: MemberUserInfo | None = None

    @classmethod
    def from_orm(cls, m: ProjectMember, user: object = None) -> "MemberResponse":
        return cls(
            id=m.id,
            project_id=m.project_id,
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at.isoformat(),
            removed_at=m.removed_at.isoformat() if m.removed_at else None,
            is_active=m.removed_at is None,
            user=MemberUserInfo(
                id=str(user.id),  # type: ignore[attr-defined]
                username=user.username,  # type: ignore[attr-defined]
                full_name=user.full_name,  # type: ignore[attr-defined]
            )
            if user
            else None,
        )


# ── Dependency: obtener membresía activa del usuario en el proyecto ────────────


async def get_project_member(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectMember:
    """
    Valida que el usuario tiene membresía activa en el proyecto.
    Admins del sistema tienen acceso aunque no sean miembros explícitos.
    Retorna 403 (no 404) si no hay membresía — no revela existencia del proyecto.
    R-0202
    """
    repo = ProjectRepository(db)

    project = await repo.get_active(project_id)
    if not project:
        raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

    if current_user.role == "admin":
        membership = await repo.get_active_membership(project_id, current_user.id)
        if membership:
            return membership
        virtual = ProjectMember()
        virtual.project_id = project_id
        virtual.user_id = current_user.id
        virtual.role = "editor"
        virtual.removed_at = None
        virtual.joined_at = project.created_at
        return virtual

    membership = await repo.get_active_membership(project_id, current_user.id)
    if not membership:
        raise InsufficientPermissionsError()
    return membership


ProjectMembership = Annotated[ProjectMember, Depends(get_project_member)]


# ── CRUD proyectos ─────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=201,
    responses={
        403: {"description": "Sin permisos — solo editor o admin puede crear"},
        422: {"description": "PROJECT_LIMIT_REACHED — límite de proyectos alcanzado"},
    },
)
async def create_project(
    body: ProjectCreateRequest,
    current_user: CurrentUser,
    db: DB,
):
    """
    Crea un proyecto. Solo editors y admins pueden crear.
    El creador queda automáticamente como owner en project_members.
    Valida límite de proyectos desde system_settings (default 20).
    R-0301
    """
    service = ProjectService(db)
    project = await service.create(body.name, body.description, current_user)
    return ProjectResponse.from_orm(project, my_role="owner")


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    current_user: CurrentUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
):
    """
    Lista proyectos donde el usuario es miembro activo.
    Incluye my_role (rol del usuario en cada proyecto) y member_count.
    R-0301
    """
    page_size = min(max(page_size, 1), 100)
    repo = ProjectRepository(db)
    items, total = await repo.list_by_user(current_user.id, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    project_ids = [p.id for p in items]
    memberships: dict = {}
    if project_ids:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id.in_(project_ids),
                ProjectMember.user_id == current_user.id,
                ProjectMember.removed_at.is_(None),
            )
        )
        for m in result.scalars().all():
            memberships[m.project_id] = m.role

    member_counts: dict = {}
    if project_ids:
        count_result = await db.execute(
            select(ProjectMember.project_id, func.count(ProjectMember.id))
            .where(
                ProjectMember.project_id.in_(project_ids),
                ProjectMember.removed_at.is_(None),
            )
            .group_by(ProjectMember.project_id)
        )
        for project_id, count in count_result.all():
            member_counts[project_id] = count

    def resolve_role(p: Project) -> str:
        if p.id in memberships:
            return memberships[p.id]
        if current_user.role == "admin":
            return "admin"
        if p.owner_id == current_user.id:
            return "owner"
        return "member"

    return PaginatedResponse(
        items=[
            ProjectResponse.from_orm(
                p,
                my_role=resolve_role(p),
                member_count=member_counts.get(p.id, 0),
            )
            for p in items
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={
        403: {"description": "Sin membresía activa en el proyecto"},
        404: {"description": "Proyecto no encontrado"},
    },
)
async def get_project(
    project_id: UUID,
    membership: ProjectMembership,
    db: DB,
):
    """
    Detalle de un proyecto. Cualquier miembro activo puede leer (incluye
    viewer). Mismo patrón de acceso que list_members/member_history —
    reutiliza get_project_member vía ProjectMembership (403 si no hay
    membresía, 404 si el proyecto no existe o está eliminado).

    Cierra el gap arrastrado de Sprint 3: el tablero de Frontend
    (BoardPage.jsx) dependía de location.state para mostrar nombre/rol
    del proyecto, lo que se rompía con F5 o un link compartido directo.
    """
    repo = ProjectRepository(db)
    project = await repo.get_active(project_id)
    if not project:
        raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

    count_result = await db.execute(
        select(func.count(ProjectMember.id)).where(
            ProjectMember.project_id == project_id,
            ProjectMember.removed_at.is_(None),
        )
    )
    member_count = count_result.scalar_one()

    return ProjectResponse.from_orm(
        project, my_role=membership.role, member_count=member_count
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={
        403: {"description": "Sin permisos — solo owner o admin puede editar"},
        404: {"description": "Proyecto no encontrado"},
    },
)
async def update_project(
    project_id: UUID,
    body: ProjectUpdateRequest,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """Solo owner del proyecto o admin del sistema puede editar. R-0301"""
    if membership.role != "owner" and current_user.role != "admin":
        raise InsufficientPermissionsError()

    repo = ProjectRepository(db)
    project = await repo.get_active(project_id)
    if not project:
        raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name.strip()
    if body.description is not None:
        updates["description"] = body.description

    if updates:
        from datetime import datetime  # noqa: PLC0415

        from sqlalchemy import update as sa_update  # noqa: PLC0415

        updates["updated_at"] = datetime.now(UTC)
        await db.execute(
            sa_update(Project).where(Project.id == project_id).values(**updates)
        )
        await db.commit()
        project = await repo.get_active(project_id)
        if not project:
            raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

    return ProjectResponse.from_orm(project, my_role=membership.role)


@router.delete(
    "/{project_id}",
    status_code=204,
    responses={
        403: {"description": "Sin permisos — solo owner o admin puede eliminar"},
        404: {"description": "Proyecto no encontrado"},
        409: {
            "description": "PROJECT_HAS_ACTIVE_TASKS — el proyecto tiene tareas activas"
        },
    },
)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """
    Soft delete. Solo owner o admin puede eliminar.
    Rechaza con 409 si tiene tareas activas — lista las primeras 10.
    R-0302
    """
    if membership.role != "owner" and current_user.role != "admin":
        raise InsufficientPermissionsError()

    service = ProjectService(db)
    await service.soft_delete(project_id, current_user)


# ── Gestión de miembros ────────────────────────────────────────────────────────


@router.get(
    "/{project_id}/members",
    response_model=list[MemberResponse],
    responses={
        403: {"description": "Sin membresía activa en el proyecto"},
        404: {"description": "Proyecto no encontrado"},
    },
)
async def list_members(
    project_id: UUID,
    membership: ProjectMembership,
    db: DB,
):
    """Lista miembros activos del proyecto. R-0303"""
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.removed_at.is_(None),
        )
        .order_by(ProjectMember.joined_at.asc())
    )
    rows = result.all()
    return [MemberResponse.from_orm(m, user=u) for m, u in rows]


@router.post(
    "/{project_id}/members",
    response_model=MemberResponse,
    status_code=201,
    responses={
        403: {"description": "Sin permisos — solo owner o editor puede agregar"},
        404: {"description": "Usuario a agregar no encontrado"},
        409: {"description": "MEMBER_ALREADY_EXISTS — el usuario ya es miembro activo"},
    },
)
async def add_member(
    project_id: UUID,
    body: AddMemberRequest,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """
    Agrega miembro. Solo owner o editor puede agregar.
    Un editor NO puede asignar rol owner — previene escalada de privilegios.
    R-0303
    """
    service = ProjectService(db)
    new_member = await service.add_member(
        project_id, body.user_id, body.role, current_user, membership
    )
    return MemberResponse.from_orm(new_member)


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=204,
    responses={
        403: {"description": "Sin permisos — solo owner o editor puede remover"},
        404: {"description": "Miembro no encontrado"},
        409: {
            "description": "CANNOT_REMOVE_OWNER — no se puede remover al owner directamente"
        },
    },
)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """
    Soft delete de membresía (removed_at). El owner no puede ser removido directamente —
    transfiere el ownership primero. R-0303
    """
    service = ProjectService(db)
    await service.remove_member(project_id, user_id, current_user, membership)


@router.get(
    "/{project_id}/members/history",
    response_model=PaginatedResponse[MemberResponse],
    responses={
        403: {"description": "Sin permisos — solo owner, editor o admin"},
        404: {"description": "Proyecto no encontrado"},
    },
)
async def member_history(
    project_id: UUID,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
    page: int = 1,
    page_size: int = 20,
):
    """
    Historial completo de membresías (activas + removidas).
    Solo accesible para owner, editor o admin. R-0306
    """
    if membership.role not in ("owner", "editor") and current_user.role != "admin":
        raise InsufficientPermissionsError()

    page_size = min(max(page_size, 1), 100)
    repo = ProjectRepository(db)
    items, total = await repo.list_member_history(project_id, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(
        items=[MemberResponse.from_orm(m) for m in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
    )


@router.post(
    "/{project_id}/transfer-ownership",
    response_model=MessageResponse,
    responses={
        403: {"description": "Sin permisos — solo el owner actual puede transferir"},
        404: {
            "description": "NOT_FOUND — el nuevo owner no es miembro activo del proyecto"
        },
        409: {
            "description": "INVALID_OPERATION — no puedes transferirte el ownership a ti mismo"
        },
    },
)
async def transfer_ownership(
    project_id: UUID,
    body: TransferOwnershipRequest,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """
    Transferencia atómica de ownership. Solo el owner actual puede transferir.
    El nuevo owner debe ser miembro activo. El owner anterior pasa a rol editor.
    Registrado en audit_logs. DU-02 · R-0304
    """
    service = ProjectService(db)
    await service.transfer_ownership(
        project_id, body.new_owner_id, current_user, membership
    )
    return MessageResponse(message="Ownership transferido exitosamente.")


# ── Invitaciones (E03 · Sprint 4 · Objetivos 7 y 9) ───────────────────────
# La tabla project_invitations y el modelo ProjectInvitation ya existían
# desde la migración 0001 (Sprint 1, DU-02) — nunca se habían wireado
# repository/service/endpoints. accept/reject viven en su propio router
# (invitations.py) porque no dependen de un project_id en la URL: el token
# es suficiente para resolver todo.


@router.post(
    "/{project_id}/invitations",
    response_model=InvitationOut,
    status_code=201,
    responses={
        403: {"description": "Sin permisos — solo owner o admin puede invitar"},
        404: {"description": "Proyecto no encontrado"},
        409: {"description": "INVITATION_ALREADY_PENDING o MEMBER_ALREADY_EXISTS"},
        429: {"description": "INVITATION_RATE_LIMIT_EXCEEDED — máximo 10/proyecto/día"},
    },
)
async def create_invitation(
    project_id: UUID,
    body: InvitationCreate,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """Invita por email a colaborar en el proyecto. Rol limitado a
    viewer/editor (nunca owner/admin — previene escalada de privilegios,
    mismo riesgo que ya se cubrió en E03 para add_member)."""
    service = InvitationService(db)
    return await service.create_invitation(
        project_id=project_id,
        email=body.email,
        role=body.role,
        actor=current_user,
        membership=membership,
    )


@router.delete(
    "/{project_id}/invitations/{invitation_id}",
    status_code=204,
    responses={
        403: {"description": "Sin permisos — solo owner o admin puede cancelar"},
        404: {"description": "Invitación no encontrada"},
        409: {"description": "Solo se pueden cancelar invitaciones pendientes"},
    },
)
async def cancel_invitation(
    project_id: UUID,
    invitation_id: UUID,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """Cancela una invitación pendiente. Queda marcada 'expired' (no se
    borra el registro) — trazabilidad. R-0308/R-0309"""
    service = InvitationService(db)
    await service.cancel_invitation(
        project_id=project_id,
        invitation_id=invitation_id,
        actor=current_user,
        membership=membership,
    )
