"""
Router: /projects — E03 Gestión de proyectos y membresía
Sprint 2 · E03 · R-0301 a R-0307

Los routers no tienen lógica de negocio. Solo:
  1. Reciben el request y validan schemas Pydantic
  2. Llaman al service correspondiente
  3. Retornan el response

ART-08 (migración), ART-09 (CRUD), ART-10 (miembros), ART-11 (ownership),
ART-12 (historial)
"""
import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role, verify_project_membership
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.project import (
    AddMemberRequest,
    OwnershipTransferResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
    TransferOwnershipRequest,
)
from app.core.security import get_current_user
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── CRUD proyectos ────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear proyecto",
    description="Solo editors y admins pueden crear proyectos. El creador queda como owner.",
)
async def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.create_project(payload, current_user)
    return ProjectResponse.from_orm(project)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="Listar proyectos del usuario",
    description="Lista proyectos donde el usuario es miembro activo. Paginado.",
)
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    current_user: Annotated[User, Depends(get_current_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> ProjectListResponse:
    page_size = min(max(page_size, 1), 100)
    service = ProjectService(db)
    items, total = await service.list_projects(current_user, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return ProjectListResponse(
        items=[ProjectResponse.from_orm(p) for p in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Actualizar proyecto",
    description="Solo el owner o admin del sistema puede editar.",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.update_project(project_id, payload, current_user, membership)
    return ProjectResponse.from_orm(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar proyecto (soft delete)",
    description=(
        "Rechaza con 409 si el proyecto tiene tareas activas. "
        "Solo owner o admin puede eliminar."
    ),
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = ProjectService(db)
    await service.delete_project(project_id, current_user, membership)


# ── Gestión de miembros ───────────────────────────────────────────────────────

@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
    summary="Listar miembros activos del proyecto",
)
async def list_members(
    project_id: uuid.UUID,
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProjectMemberResponse]:
    from app.repositories.project_repository import ProjectRepository  # noqa: PLC0415
    repo = ProjectRepository(db)
    members = await repo.list_active_members(project_id)
    return [ProjectMemberResponse.from_orm_with_user(m) for m in members]


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar miembro al proyecto",
    description="Solo owner o editor puede agregar. Un editor no puede asignar rol owner.",
)
async def add_member(
    project_id: uuid.UUID,
    payload: AddMemberRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectMemberResponse:
    service = ProjectService(db)
    new_member = await service.add_member(
        project_id, payload.user_id, payload.role, current_user, membership
    )
    return ProjectMemberResponse.from_orm_with_user(new_member)


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover miembro del proyecto",
    description="Soft delete de membresía. El owner no puede ser removido directamente.",
)
async def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = ProjectService(db)
    await service.remove_member(project_id, user_id, current_user, membership)


@router.get(
    "/{project_id}/members/history",
    summary="Historial de membresías",
    description="Incluye miembros removidos. Solo owner o admin.",
)
async def member_history(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> dict:
    import math as _math  # noqa: PLC0415
    service = ProjectService(db)
    items, total = await service.get_member_history(
        project_id, current_user, membership, page, min(page_size, 100)
    )
    total_pages = _math.ceil(total / page_size) if total > 0 else 1
    return {
        "items": [ProjectMemberResponse.from_orm_with_user(m) for m in items],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "next_page": page + 1 if page < total_pages else None,
        "previous_page": page - 1 if page > 1 else None,
    }


# ── Transferencia de ownership ────────────────────────────────────────────────

@router.post(
    "/{project_id}/transfer-ownership",
    response_model=OwnershipTransferResponse,
    summary="Transferir ownership del proyecto",
    description=(
        "Solo el owner actual puede transferir. "
        "El nuevo owner debe ser miembro activo. "
        "Operación atómica registrada en audit_logs."
    ),
)
async def transfer_ownership(
    project_id: uuid.UUID,
    payload: TransferOwnershipRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[ProjectMember, Depends(verify_project_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OwnershipTransferResponse:
    service = ProjectService(db)
    prev_owner, new_owner = await service.transfer_ownership(
        project_id, payload.new_owner_id, current_user, membership
    )
    return OwnershipTransferResponse(
        previous_owner=ProjectMemberResponse.from_orm_with_user(prev_owner),
        new_owner=ProjectMemberResponse.from_orm_with_user(new_owner),
    )