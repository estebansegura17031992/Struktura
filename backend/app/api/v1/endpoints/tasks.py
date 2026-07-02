"""
Endpoints de gestión de tareas (E04 · R-0401 a R-0408).

Entrega PM: Backend Día 3. CRUD funcional en el entorno compartido:
  POST   /tasks                 – crear tarea
  GET    /tasks/{task_id}       – detalle de tarea
  PATCH  /tasks/{task_id}       – editar tarea
  DELETE /tasks/{task_id}       – soft delete
  PATCH  /tasks/{task_id}/status – cambiar estado

RBAC heredado de E02/E03 (pedido explícito del PM: no reimplementar).
NOTA DE DISEÑO (para que Security no se sorprenda al comparar con projects.py):
  `app/dependencies.py` (require_role/verify_project_membership, ART-01/ART-02)
  NO está wireado a ningún router real — `projects.py` (E03, ya en producción)
  define su propia dependencia local `get_project_member` en vez de usarlo.
  Este archivo sigue ESE patrón real (local, basado en ProjectRepository),
  no el de `app/dependencies.py`, que está muerto.
  A diferencia de `projects.py` (que sí tiene `if membership.role != "owner"...`
  inline en update_project/delete_project), aquí el chequeo de rol se
  envuelve en `require_task_role(...)` como dependencia — el PM pidió
  explícitamente que los endpoints nuevos NO tengan lógica de permisos
  inline, para que Security lo revise limpio.

Ubicación en el repo: backend/app/api/v1/endpoints/tasks.py
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import DB, CurrentUser, get_current_user
from app.api.deps.db import get_db
from app.core.exceptions import AppBaseError, InsufficientPermissionsError
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.task import TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── Dependencia: membresía de proyecto resuelta desde una tarea existente ──
#
# Mismo criterio que `get_project_member` de projects.py (admin del sistema
# tiene bypass con membresía "virtual" editor; error 403 en vez de 404 para
# no revelar existencia), pero resolviendo `project_id` desde el `task_id`
# de la URL en lugar de tomarlo directo del path, porque estas rutas no
# tienen `{project_id}` en la URL.


async def _get_project_member_for(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> ProjectMember:
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
    """Para GET/PATCH/DELETE/status — resuelve la membresía a partir de una tarea existente."""
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
        403: {"description": "Sin permisos — solo owner o editor puede mover la tarea"},
        404: {"description": "Tarea no encontrada"},
    },
)
async def update_task_status(
    task_id: UUID,
    body: TaskStatusUpdate,
    db: DB,
    _membership: Annotated[ProjectMember, Depends(require_task_role("owner", "editor"))],
):
    """Cambia el estado (abierto/en_proceso/completo) — mover tarjeta en el Kanban."""
    service = TaskService(db)
    return await service.update_status(task_id, payload=body)