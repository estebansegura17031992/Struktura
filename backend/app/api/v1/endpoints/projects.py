"""
Endpoints de gestión de proyectos y membresía (E03 · R-0301 a R-0307).

Todos los endpoints de proyecto requieren membresía activa o rol admin,
validado mediante get_project_member() dependency.

Endpoints:
  POST   /projects                              — crear proyecto
  GET    /projects                              — listar proyectos del usuario
  PATCH  /projects/{project_id}                 — editar proyecto
  DELETE /projects/{project_id}                 — soft delete
  GET    /projects/{project_id}/members         — listar miembros activos
  POST   /projects/{project_id}/members         — agregar miembro
  DELETE /projects/{project_id}/members/{uid}   — remover miembro
  GET    /projects/{project_id}/members/history — historial de membresías
  POST   /projects/{project_id}/transfer-ownership — transferir ownership
"""
import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import DB, CurrentUser, get_current_user
from app.api.deps.db import get_db
from app.core.exceptions import AppBaseError, InsufficientPermissionsError, UserNotFoundError
from app.core.logging import get_logger
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.audit_service import log_action
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger(__name__)


# ── Schemas inline ────────────────────────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar en blanco")
        return v.strip()


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class AddMemberRequest(BaseModel):
    user_id: UUID
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"owner", "editor", "viewer"}:
            raise ValueError("Rol inválido. Permitidos: owner, editor, viewer")
        return v


class TransferOwnershipRequest(BaseModel):
    new_owner_id: UUID


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, p: Project) -> "ProjectResponse":
        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            owner_id=p.owner_id,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )


class MemberResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    role: str
    joined_at: str
    removed_at: str | None
    is_active: bool

    @classmethod
    def from_orm(cls, m: ProjectMember) -> "MemberResponse":
        return cls(
            id=m.id,
            project_id=m.project_id,
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at.isoformat(),
            removed_at=m.removed_at.isoformat() if m.removed_at else None,
            is_active=m.removed_at is None,
        )


# ── Dependency: obtener membresía activa del usuario en el proyecto ───────────

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
    # Importamos aquí para evitar circular import
    repo = ProjectRepository(db)

    # Verificar que el proyecto existe y no está eliminado
    project = await repo.get_active(project_id)
    if not project:
        raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

    # Admins del sistema acceden a cualquier proyecto
    if current_user.role == "admin":
        # Buscar membresía real o devolver membresía virtual con rol editor
        membership = await repo.get_active_membership(project_id, current_user.id)
        if membership:
            return membership
        # Membresía virtual para admin sin membresía explícita
        virtual = ProjectMember()
        virtual.project_id = project_id
        virtual.user_id = current_user.id
        virtual.role = "editor"
        virtual.removed_at = None
        virtual.joined_at = project.created_at
        return virtual

    # Usuarios normales requieren membresía activa
    membership = await repo.get_active_membership(project_id, current_user.id)
    if not membership:
        raise InsufficientPermissionsError()

    return membership


# Tipo anotado para uso limpio en endpoints
ProjectMembership = Annotated[ProjectMember, Depends(get_project_member)]


# ── CRUD proyectos ────────────────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=201)
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
    return ProjectResponse.from_orm(project)


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    current_user: CurrentUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
):
    """Lista proyectos donde el usuario es miembro activo. R-0301"""
    page_size = min(max(page_size, 1), 100)
    repo = ProjectRepository(db)
    items, total = await repo.list_by_user(current_user.id, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(
        items=[ProjectResponse.from_orm(p) for p in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
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
        from sqlalchemy import update as sa_update  # noqa: PLC0415
        from datetime import datetime, timezone  # noqa: PLC0415
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.execute(
            sa_update(Project).where(Project.id == project_id).values(**updates)
        )
        await db.commit()
        project = await repo.get_active(project_id)
        if not project:
            raise AppBaseError("NOT_FOUND", "Proyecto no encontrado.", 404)

    return ProjectResponse.from_orm(project)


@router.delete("/{project_id}", status_code=204)
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


# ── Gestión de miembros ───────────────────────────────────────────────────────

@router.get("/{project_id}/members", response_model=list[MemberResponse])
async def list_members(
    project_id: UUID,
    membership: ProjectMembership,
    db: DB,
):
    """Lista miembros activos del proyecto. R-0303"""
    repo = ProjectRepository(db)
    members = await repo.list_active_members(project_id)
    return [MemberResponse.from_orm(m) for m in members]


@router.post("/{project_id}/members", response_model=MemberResponse, status_code=201)
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


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """
    Soft delete de membresía. El owner no puede ser removido directamente.
    R-0303
    """
    service = ProjectService(db)
    await service.remove_member(project_id, user_id, current_user, membership)


@router.get("/{project_id}/members/history",
            response_model=PaginatedResponse[MemberResponse])
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
    Solo accesible para owner o admin. R-0306
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


@router.post("/{project_id}/transfer-ownership", response_model=MessageResponse)
async def transfer_ownership(
    project_id: UUID,
    body: TransferOwnershipRequest,
    current_user: CurrentUser,
    membership: ProjectMembership,
    db: DB,
):
    """
    Transferencia atómica de ownership. Solo el owner actual puede transferir.
    El nuevo owner debe ser miembro activo. Registrado en audit_logs.
    DU-02 · R-0304
    """
    service = ProjectService(db)
    await service.transfer_ownership(
        project_id, body.new_owner_id, current_user, membership
    )
    return MessageResponse(message="Ownership transferido exitosamente.")