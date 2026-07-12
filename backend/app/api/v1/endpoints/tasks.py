"""
Endpoints de gestión de tareas (E04 · R-0401 a R-0409).

Alcance de este archivo (PM confirmó: todo va en un solo PR, no se separa):
  POST   /tasks                  – crear tarea
  GET    /tasks                  – listar con filtros + FTS + paginación (R-0403/04/05)
  GET    /tasks/{task_id}        – detalle de tarea
  PATCH  /tasks/{task_id}        – editar tarea
  DELETE /tasks/{task_id}        – soft delete
  PATCH  /tasks/{task_id}/status – cambiar estado (R-0402/R-0409)
  PATCH  /tasks/{task_id}/assignees – asignación múltiple + ADR-03 (R-0407)

RBAC heredado de E02/E03. `app/dependencies.py` (require_role/
verify_project_membership) NO está wireado a ningún router real —
`projects.py` (E03, en producción) define su propia dependencia local
`get_project_member`. Este archivo sigue ESE patrón real, adaptado para
resolver `project_id` desde una tarea existente o desde query/body cuando
no hay `{project_id}` en la URL. A diferencia de `projects.py` (que tiene
`if membership.role != "owner"...` inline), aquí el chequeo de rol vive en
dependencias (`require_task_role`, `require_task_status_permission`) — sin
lógica de permisos inline en los endpoints, por pedido explícito del PM.

Ubicación en el repo: backend/app/api/v1/endpoints/tasks.py
"""
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import DB, CurrentUser, get_current_user
from app.api.deps.db import get_db
from app.core.exceptions import AppBaseError, InsufficientPermissionsError
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task import (
    TaskAssigneesUpdate,
    TaskCreate,
    TaskListItem,
    TaskOut,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── Dependencia base: resuelve membresía de proyecto contra ProjectRepository ──


async def _get_project_member_for(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> ProjectMember:
    """Mismo criterio que `get_project_member` de projects.py (admin bypass con
    membresía virtual editor; 403 en vez de 404 para no revelar existencia)."""
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


async def get_task_project_member(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectMember:
    """Para GET/PATCH/DELETE/status/assignees — resuelve membresía desde una tarea existente."""
    service = TaskService(db)
    project_id = await service.get_task_project_id(task_id)
    return await _get_project_member_for(project_id, current_user, db)


async def get_project_member_for_create(
    body: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectMember:
    """Para POST /tasks — no hay tarea todavía; project_id viene del body."""
    return await _get_project_member_for(body.project_id, current_user, db)


async def get_project_member_for_list(
    project_id: Annotated[UUID, Query(..., description="Proyecto a listar (requerido)")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectMember:
    """Para GET /tasks — project_id viene de query param, no de la URL."""
    return await _get_project_member_for(project_id, current_user, db)


def require_task_role(*allowed_roles: str):
    """Factory de dependencia — reemplaza el chequeo inline que sí existe en
    projects.py, por pedido explícito del PM para los endpoints de E04."""

    async def _check(
        membership: Annotated[ProjectMember, Depends(get_task_project_member)],
    ) -> ProjectMember:
        if membership.role not in allowed_roles:
            raise InsufficientPermissionsError()
        return membership

    return _check


def require_project_role_for_create(*allowed_roles: str):
    async def _check(
        membership: Annotated[ProjectMember, Depends(get_project_member_for_create)],
    ) -> ProjectMember:
        if membership.role not in allowed_roles:
            raise InsufficientPermissionsError()
        return membership

    return _check


async def require_task_status_permission(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[ProjectMember, Depends(get_task_project_member)],
) -> ProjectMember:
    """R-0402: editor/owner de proyecto siempre puede. Un asignado a la tarea
    también puede, EXCEPTO si su rol de proyecto es viewer (viewer nunca puede
    cambiar estado, ni siquiera estando asignado — regla explícita del PM)."""
    if membership.role in ("owner", "editor"):
        return membership

    if membership.role == "viewer":
        service = TaskService(db)
        if await service.is_assignee(task_id, current_user.id):
            # Viewer asignado: sigue sin poder, por regla explícita R-0402.
            raise InsufficientPermissionsError()

    raise InsufficientPermissionsError()


TaskMembership = Annotated[ProjectMember, Depends(get_task_project_member)]


# ── CRUD ─────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=TaskOut,
    status_code=201,
    responses={
        403: {"description": "Sin permisos — solo owner o editor del proyecto puede crear"},
        404: {"description": "Proyecto no encontrado"},
        422: {"description": "MAX_ASSIGNEES_EXCEEDED — supera system_settings.max_task_assignees"},
    },
)
async def create_task(
    body: TaskCreate,
    current_user: CurrentUser,
    db: DB,
    _membership: Annotated[
        ProjectMember, Depends(require_project_role_for_create("owner", "editor"))
    ],
):
    """Crea una tarea. Requiere rol owner o editor en el proyecto (viewer no puede). R-0401"""
    service = TaskService(db)
    return await service.create_task(payload=body, created_by=current_user.id)


@router.get(
    "",
    response_model=PaginatedResponse[TaskListItem],
    responses={
        403: {"description": "Viewer solo puede filtrar assigned_to=me"},
        404: {"description": "Proyecto no encontrado"},
        422: {"description": "search debe tener entre 2 y 100 caracteres"},
    },
)
async def list_tasks(
    current_user: CurrentUser,
    db: DB,
    membership: Annotated[ProjectMember, Depends(get_project_member_for_list)],
    project_id: UUID = Query(...),
    priority: str | None = Query(default=None),
    status: str | None = Query(default=None),
    assigned_to: str | None = Query(
        default=None, description="'me' o un user_id UUID. Viewer solo puede usar 'me'."
    ),
    due_date_from: date | None = Query(default=None),
    due_date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
):
    """Las 3 columnas se cargan en una sola llamada sin filtro de status
    (el frontend separa por columna). Máximo 50 tareas por página (R-0405)."""
    service = TaskService(db)
    return await service.list_tasks(
        project_id=project_id,
        priority=priority,
        status=status,
        assigned_to=assigned_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        page=page,
        page_size=page_size,
        current_user_id=current_user.id,
        is_viewer=membership.role == "viewer",
    )


@router.get(
    "/{task_id}",
    response_model=TaskOut,
    responses={
        403: {"description": "Sin membresía activa en el proyecto de la tarea"},
        404: {"description": "Tarea no encontrada"},
    },
)
async def get_task(
    task_id: UUID,
    db: DB,
    _membership: TaskMembership,
):
    """Detalle de tarea. Cualquier miembro activo del proyecto puede leer (incluye viewer)."""
    service = TaskService(db)
    return await service.get_task(task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskOut,
    responses={
        403: {"description": "Sin permisos — solo owner o editor puede editar"},
        404: {"description": "Tarea no encontrada"},
        422: {"description": "MAX_ASSIGNEES_EXCEEDED"},
    },
)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    current_user: CurrentUser,
    db: DB,
    _membership: Annotated[ProjectMember, Depends(require_task_role("owner", "editor"))],
):
    """Edición parcial de tarea. Requiere rol owner o editor. R-0401"""
    service = TaskService(db)
    return await service.update_task(task_id, payload=body, actor_id=current_user.id)


@router.delete(
    "/{task_id}",
    status_code=204,
    responses={
        403: {"description": "Sin permisos — solo owner o editor puede eliminar"},
        404: {"description": "Tarea no encontrada"},
    },
)
async def delete_task(
    task_id: UUID,
    db: DB,
    _membership: Annotated[ProjectMember, Depends(require_task_role("owner", "editor"))],
):
    """Soft delete (deleted_at). Sin recuperación por UI (AG-04). R-0401"""
    service = TaskService(db)
    await service.delete_task(task_id)


@router.patch(
    "/{task_id}/status",
    response_model=TaskOut,
    responses={
        403: {"description": "Sin permisos — editor/admin o asignado (viewer nunca puede)"},
        404: {"description": "Tarea no encontrada"},
    },
)
async def update_task_status(
    task_id: UUID,
    body: TaskStatusUpdate,
    current_user: CurrentUser,
    db: DB,
    _membership: Annotated[ProjectMember, Depends(require_task_status_permission)],
):
    """Cambia el estado — mover tarjeta en el Kanban. Editor/owner o asignado
    (viewer nunca puede, ni siquiera estando asignado). Registra audit_logs (R-0409)."""
    service = TaskService(db)
    return await service.update_status(task_id, payload=body, actor_id=current_user.id)


@router.patch(
    "/{task_id}/assignees",
    response_model=TaskOut,
    responses={
        403: {"description": "Sin permisos — solo owner o editor puede reasignar"},
        404: {"description": "Tarea no encontrada"},
        422: {"description": "MAX_ASSIGNEES_EXCEEDED o lista vacía"},
    },
)
async def update_task_assignees(
    task_id: UUID,
    body: TaskAssigneesUpdate,
    current_user: CurrentUser,
    db: DB,
    _membership: Annotated[ProjectMember, Depends(require_task_role("owner", "editor"))],
):
    """Reemplaza el set de asignados. ADR-03: al pasar de 1 a 2+ asignados con
    timer activo, se detiene automáticamente y queda registrado en audit_logs. R-0407"""
    service = TaskService(db)
    return await service.update_assignees(task_id, payload=body, actor_id=current_user.id)
