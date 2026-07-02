"""Service de `tasks` — reglas de negocio, SIN lógica de permisos/RBAC.

La verificación de rol y membresía de proyecto se resuelve exclusivamente en
`app/api/v1/endpoints/tasks.py` (dependencias `get_task_project_member` +
`require_task_role`). Este archivo no debe contener ningún `if role == ...`
ni chequeo de pertenencia a proyecto — eso es justo lo que Security revisa
en el Día 3 (pedido explícito del PM).

Ubicación en el repo: backend/app/services/task_service.py
"""
from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppBaseError
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskAssigneeOut, TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate

DEFAULT_MAX_TASK_ASSIGNEES = 5  # fallback si la fila de system_settings no existiera


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

    async def _to_task_out(self, task_id: UUID) -> TaskOut:
        task = await self._repo.get_active(task_id)
        if task is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)

        rows = await self._repo.get_assignees_with_user(task_id)
        assignees = [
            TaskAssigneeOut(
                id=user.id,
                username=user.username,
                avatar=_avatar_placeholder(user.email),
                is_active=user.deleted_at is None,
            )
            for _assignee, user in rows
        ]
        return TaskOut(
            id=task.id,
            task_number=task.task_number,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            project_id=task.project_id,
            created_by=task.created_by,
            due_date=task.due_date,
            timer_disabled=task.timer_disabled,
            assignees=assignees,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    async def _validate_assignee_count(self, count: int) -> None:
        max_assignees = await _get_max_task_assignees(self._session)
        if count > max_assignees:
            raise AppBaseError(
                "MAX_ASSIGNEES_EXCEEDED",
                f"No se pueden asignar más de {max_assignees} usuarios por tarea "
                f"(system_settings.max_task_assignees).",
                422,
            )

    async def create_task(self, *, payload: TaskCreate, created_by: UUID) -> TaskOut:
        await self._validate_assignee_count(len(payload.assignee_ids))

        task = await self._repo.create(
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

    async def update_status(self, task_id: UUID, *, payload: TaskStatusUpdate) -> TaskOut:
        existing = await self._repo.get_active(task_id)
        if existing is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)
        await self._repo.update_status(task_id, payload.status.value)
        await self._session.commit()
        return await self._to_task_out(task_id)

    async def delete_task(self, task_id: UUID) -> None:
        existing = await self._repo.get_active(task_id)
        if existing is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)
        await self._repo.soft_delete(task_id)
        await self._session.commit()

    async def get_task_project_id(self, task_id: UUID) -> UUID:
        """Usado por la dependencia de membresía del router para resolver el
        project_id de una tarea existente (los endpoints no tienen project_id en la URL)."""
        task = await self._repo.get_active(task_id)
        if task is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)
        return task.project_id