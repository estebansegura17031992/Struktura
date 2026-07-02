"""Repository de `tasks` — capa de acceso a datos, sin lógica de negocio ni de permisos.

Sigue el mismo estilo que `app/repositories/project_repository.py`:
- Fetch de entidad "viva" (`get_active`) filtrando soft-delete.
- Joins explícitos con `select(...).join(...)` para traer relaciones
  (igual que `projects.py::list_members` hace con `ProjectMember`+`User`),
  en vez de `relationship()` de SQLAlchemy — el modelo real `app/models/task.py`
  (ya existente, de otro compañero) NO define `relationship()` en `Task` ni
  en `TaskAssignee`, solo columnas FK planas. Por eso este repository no usa
  `selectinload` ni navegación de atributos tipo `task.assignees`.

Ubicación en el repo: backend/app/repositories/task_repository.py
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskAssignee
from app.models.user import User


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Lectura ──────────────────────────────────────────────────────────

    async def get_active(self, task_id: UUID) -> Task | None:
        stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignees_with_user(
        self, task_id: UUID
    ) -> Sequence[tuple[TaskAssignee, User]]:
        """Igual patrón que `projects.py::list_members` (join explícito, sin relationship())."""
        stmt = (
            select(TaskAssignee, User)
            .join(User, TaskAssignee.user_id == User.id)
            .where(TaskAssignee.task_id == task_id)
            .order_by(TaskAssignee.assigned_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.all()

    # ── Escritura ────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        priority: str,
        project_id: UUID,
        created_by: UUID,
        due_date=None,
        timer_disabled: bool = False,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            project_id=project_id,
            created_by=created_by,
            due_date=due_date,
            timer_disabled=timer_disabled,
            status="abierto",
        )
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def update_fields(self, task_id: UUID, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = datetime.now(UTC)
        await self._session.execute(
            sa_update(Task).where(Task.id == task_id).values(**fields)
        )

    async def update_status(self, task_id: UUID, status: str) -> None:
        await self._session.execute(
            sa_update(Task)
            .where(Task.id == task_id)
            .values(status=status, updated_at=datetime.now(UTC))
        )

    async def soft_delete(self, task_id: UUID) -> None:
        await self._session.execute(
            sa_update(Task)
            .where(Task.id == task_id)
            .values(deleted_at=datetime.now(UTC))
        )

    async def replace_assignees(
        self, task_id: UUID, *, assignee_ids: Sequence[UUID], assigned_by: UUID
    ) -> None:
        """Reemplaza el set completo de asignados. La validación de
        max_task_assignees vive en el service layer, no aquí."""
        await self._session.execute(
            TaskAssignee.__table__.delete().where(TaskAssignee.task_id == task_id)
        )
        for user_id in assignee_ids:
            self._session.add(
                TaskAssignee(task_id=task_id, user_id=user_id, assigned_by=assigned_by)
            )