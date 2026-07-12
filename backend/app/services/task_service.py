"""Service de `tasks` — reglas de negocio, SIN lógica de permisos/RBAC.

La verificación de rol y membresía de proyecto se resuelve exclusivamente en
`app/api/v1/endpoints/tasks.py`. Este archivo no debe contener ningún
`if role == ...` ni chequeo de pertenencia a proyecto — eso es justo lo que
Security revisa (pedido explícito del PM).

Ubicación en el repo: backend/app/services/task_service.py
"""
from __future__ import annotations

import hashlib
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppBaseError
from app.repositories.task_repository import TaskRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task import (
    TaskAssigneeOut,
    TaskAssigneesUpdate,
    TaskCreate,
    TaskListItem,
    TaskOut,
    TaskPriority,
    TaskStatus,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.audit_service import log_action

DEFAULT_MAX_TASK_ASSIGNEES = 5  # fallback si la fila de system_settings no existiera
MIN_SEARCH_LEN = 2
MAX_SEARCH_LEN = 100


async def _get_max_task_assignees(session: AsyncSession) -> int:
    """Lee system_settings.max_task_assignees (corregido a 5 en la migración 0003)."""
    result = await session.execute(
        text("SELECT value FROM system_settings WHERE key = 'max_task_assignees'")
    )
    row = result.first()
    if row is None:
        return DEFAULT_MAX_TASK_ASSIGNEES
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return DEFAULT_MAX_TASK_ASSIGNEES


def _avatar_placeholder(email: str | None) -> str | None:
    """`users` no tiene columna avatar (ver nota de asunción en schemas/task.py).
    Se resuelve con Gravatar por hash de email como placeholder hasta que
    Producto decida el origen real."""
    if not email:
        return None
    email_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TaskRepository(session)

    # ── Composición de DTO ───────────────────────────────────────────────

    async def _assignees_out(self, task_id: UUID) -> list[TaskAssigneeOut]:
        rows = await self._repo.get_assignees_with_user(task_id)
        return [
            TaskAssigneeOut(
                id=user.id,
                username=user.username,
                avatar=_avatar_placeholder(user.email),
                is_active=user.deleted_at is None,
            )
            for _assignee, user in rows
        ]

    async def _to_task_out(self, task_id: UUID) -> TaskOut:
        task = await self._repo.get_active(task_id)
        if task is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)
        assignees = await self._assignees_out(task_id)
        return TaskOut(
            id=task.id,
            task_number=task.task_number,
            title=task.title,
            description=task.description,
            priority=TaskPriority(task.priority),
            status=TaskStatus(task.status),
            project_id=task.project_id,
            created_by=task.created_by,
            due_date=task.due_date,
            timer_disabled=task.timer_disabled,
            assignees=assignees,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    async def _validate_assignee_count(self, count: int) -> int:
        max_assignees = await _get_max_task_assignees(self._session)
        if count > max_assignees:
            raise AppBaseError(
                "MAX_ASSIGNEES_EXCEEDED",
                f"No se pueden asignar más de {max_assignees} usuarios por tarea "
                f"(system_settings.max_task_assignees).",
                422,
            )
        return max_assignees

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def create_task(self, *, payload: TaskCreate, created_by: UUID) -> TaskOut:
        await self._validate_assignee_count(len(payload.assignee_ids))

        task = await self._repo.create_task(
            title=payload.title,
            description=payload.description,
            priority=payload.priority.value,
            project_id=payload.project_id,
            created_by=created_by,
            due_date=payload.due_date,
            timer_disabled=payload.timer_disabled,
        )
        if payload.assignee_ids:
            await self._repo.replace_assignees(
                task.id, assignee_ids=payload.assignee_ids, assigned_by=created_by
            )
            if len(payload.assignee_ids) >= 2:
                await self._repo.set_timer_disabled(task.id, True)
        await self._session.commit()
        return await self._to_task_out(task.id)

    async def get_task(self, task_id: UUID) -> TaskOut:
        return await self._to_task_out(task_id)

    async def update_task(self, task_id: UUID, *, payload: TaskUpdate, actor_id: UUID) -> TaskOut:
        existing = await self._repo.get_active(task_id)
        if existing is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)

        update_fields = payload.model_dump(exclude_unset=True, exclude={"assignee_ids"})
        if "priority" in update_fields and update_fields["priority"] is not None:
            update_fields["priority"] = update_fields["priority"].value
        await self._repo.update_fields(task_id, **update_fields)

        if payload.assignee_ids is not None:
            await self._validate_assignee_count(len(payload.assignee_ids))
            await self._repo.replace_assignees(
                task_id, assignee_ids=payload.assignee_ids, assigned_by=actor_id
            )

        await self._session.commit()
        return await self._to_task_out(task_id)

    async def update_status(
        self, task_id: UUID, *, payload: TaskStatusUpdate, actor_id: UUID
    ) -> TaskOut:
        """R-0402/R-0409: cambia el estado y registra en audit_logs."""
        existing = await self._repo.get_active(task_id)
        if existing is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)

        old_status = existing.status
        new_status = payload.status.value
        await self._repo.update_status(task_id, new_status)

        await log_action(
            self._session,
            action="task_status_change",
            user_id=actor_id,
            entity_type="task",
            entity_id=task_id,
            metadata={"old_status": old_status, "new_status": new_status},
        )

        await self._session.commit()
        return await self._to_task_out(task_id)

    async def delete_task(self, task_id: UUID) -> None:
        existing = await self._repo.get_active(task_id)
        if existing is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)
        await self._repo.soft_delete(task_id)
        await self._session.commit()

    async def get_task_project_id(self, task_id: UUID) -> UUID:
        task = await self._repo.get_active(task_id)
        if task is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)
        return task.project_id

    async def is_assignee(self, task_id: UUID, user_id: UUID) -> bool:
        """Usado por la dependencia de permisos de status (R-0402: asignado puede
        cambiar estado incluso sin ser editor, salvo que su rol de proyecto sea viewer)."""
        rows = await self._repo.get_assignees_with_user(task_id)
        return any(assignee.user_id == user_id for assignee, _user in rows)

    # ── Listado con filtros + FTS (R-0403/R-0404/R-0405) ────────────────

    async def list_tasks(
        self,
        *,
        project_id: UUID,
        priority: str | None,
        status: str | None,
        assigned_to: str | None,
        due_date_from: date | None,
        due_date_to: date | None,
        search: str | None,
        page: int,
        page_size: int,
        current_user_id: UUID,
        is_viewer: bool,
    ) -> PaginatedResponse[TaskListItem]:
        if search is not None:
            if len(search) < MIN_SEARCH_LEN:
                raise AppBaseError(
                    "VALIDATION_ERROR",
                    f"La búsqueda requiere al menos {MIN_SEARCH_LEN} caracteres.",
                    422,
                )
            search = search[:MAX_SEARCH_LEN]

        assigned_to_user_id: UUID | None = None
        if assigned_to is not None:
            if assigned_to == "me":
                assigned_to_user_id = current_user_id
            elif is_viewer:
                # R-0403: viewer solo puede filtrar assigned_to=me
                raise AppBaseError(
                    "FORBIDDEN",
                    "Como viewer, solo puedes filtrar tareas asignadas a ti (assigned_to=me).",
                    403,
                )
            else:
                try:
                    assigned_to_user_id = UUID(assigned_to)
                except ValueError:
                    raise AppBaseError(
                        "VALIDATION_ERROR", "assigned_to debe ser 'me' o un UUID válido.", 422
                    ) from None

        page_size_applied = min(max(page_size, 1), 50)  # R-0405: máx 50 por columna

        items, total = await self._repo.list_by_project(
            project_id=project_id,
            priority=priority,
            status=status,
            assigned_to_user_id=assigned_to_user_id,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
            search=search,
            page=page,
            page_size=page_size_applied,
        )

        out_items = []
        for task in items:
            assignees = await self._assignees_out(task.id)
            out_items.append(
                TaskListItem(
                    id=task.id,
                    task_number=task.task_number,
                    title=task.title,
                    description=task.description,
                    priority=TaskPriority(task.priority),
                    status=TaskStatus(task.status),
                    project_id=task.project_id,
                    created_by=task.created_by,
                    due_date=task.due_date,
                    timer_disabled=task.timer_disabled,
                    assignees=assignees,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                )
            )

        total_pages = -(-total // page_size_applied) if total > 0 else 1
        return PaginatedResponse[TaskListItem](
            items=out_items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            next_page=page + 1 if page < total_pages else None,
            previous_page=page - 1 if page > 1 else None,
            page_size_applied=page_size_applied if page_size_applied != page_size else None,
        )

    # ── Asignación múltiple + ADR-03 (R-0407) ───────────────────────────

    async def update_assignees(
        self, task_id: UUID, *, payload: TaskAssigneesUpdate, actor_id: UUID
    ) -> TaskOut:
        existing = await self._repo.get_active(task_id)
        if existing is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)

        max_assignees = await self._validate_assignee_count(len(payload.assignee_ids))
        previous_count = await self._repo.count_assignees(task_id)
        new_count = len(payload.assignee_ids)

        await self._repo.replace_assignees(
            task_id, assignee_ids=payload.assignee_ids, assigned_by=actor_id
        )

        # ADR-03: al pasar de <=1 a >=2 asignados, detener timer activo si existe.
        if previous_count <= 1 and new_count >= 2:
            active_timer = await self._repo.get_active_timer(task_id)
            if active_timer is not None:
                await self._repo.stop_timer(active_timer, reason="multi_assignee")
                await log_action(
                    self._session,
                    action="timer_stopped_multi_assignee",
                    user_id=actor_id,
                    entity_type="task",
                    entity_id=task_id,
                    metadata={
                        "previous_assignee_count": previous_count,
                        "new_assignee_count": new_count,
                        "stopped_timer_entry_id": str(active_timer.id),
                    },
                )
            await self._repo.set_timer_disabled(task_id, True)
        elif new_count <= 1:
            # Al bajar a 1 asignado (o 0, aunque el schema no lo permite), se
            # vuelve a habilitar el timer para la tarea (R-0407).
            await self._repo.set_timer_disabled(task_id, False)

        await log_action(
            self._session,
            action="task_assignees_updated",
            user_id=actor_id,
            entity_type="task",
            entity_id=task_id,
            metadata={
                "previous_count": previous_count,
                "new_count": new_count,
                "max_allowed": max_assignees,
            },
        )

        await self._session.commit()
        return await self._to_task_out(task_id)
