"""Repository de `tasks` — capa de acceso a datos, sin lógica de negocio ni de permisos.

Hereda de `BaseRepository[Task]` (mismo patrón que `ProjectRepository`).
Usa joins explícitos (`select().join()`), no `relationship()` — el modelo
real `app/models/task.py` no las define.

Ubicación en el repo: backend/app/repositories/task_repository.py
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskAssignee, TaskTimeEntry
from app.models.user import User
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    # ── Lectura ──────────────────────────────────────────────────────────

    async def get_active(self, task_id: UUID) -> Task | None:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_assignees_with_user(
        self, task_id: UUID
    ) -> Sequence[tuple[TaskAssignee, User]]:
        result = await self.session.execute(
            select(TaskAssignee, User)
            .join(User, TaskAssignee.user_id == User.id)
            .where(TaskAssignee.task_id == task_id)
            .order_by(TaskAssignee.assigned_at.asc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def count_assignees(self, task_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(TaskAssignee)
            .where(TaskAssignee.task_id == task_id)
        )
        return result.scalar_one()

    async def list_by_project(
        self,
        *,
        project_id: UUID,
        priority: str | None = None,
        status: str | None = None,
        assigned_to_user_id: UUID | None = None,
        due_date_from: date | None = None,
        due_date_to: date | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        """Filtros combinables (AND). `search` usa el índice GIN de search_vector (R-0404)."""
        conditions: list[Any] = [Task.project_id == project_id, Task.deleted_at.is_(None)]

        if priority is not None:
            conditions.append(Task.priority == priority)
        if status is not None:
            conditions.append(Task.status == status)
        if due_date_from is not None:
            conditions.append(Task.due_date >= due_date_from)
        if due_date_to is not None:
            conditions.append(Task.due_date <= due_date_to)
        if search is not None:
            # `search_vector` es una columna generada por PostgreSQL (0001_initial_schema.py)
            # que el modelo ORM real (app/models/task.py) NO mapea como atributo Python.
            # Se usa SQL crudo con bindparam en vez de Task.search_vector para no
            # depender de un atributo que no existe en la clase declarativa.
            conditions.append(
                text("tasks.search_vector @@ plainto_tsquery('spanish', :fts_search)").bindparams(
                    fts_search=search
                )
            )

        base_q = select(Task).where(and_(*conditions))

        if assigned_to_user_id is not None:
            base_q = base_q.join(
                TaskAssignee,
                and_(
                    TaskAssignee.task_id == Task.id,
                    TaskAssignee.user_id == assigned_to_user_id,
                ),
            )

        base_q = base_q.order_by(Task.created_at.desc())

        total_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total = total_result.scalar_one()

        result = await self.session.execute(
            base_q.offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    # ── Escritura ────────────────────────────────────────────────────────

    async def create_task(
        self,
        *,
        title: str,
        description: str | None,
        priority: str,
        project_id: UUID,
        created_by: UUID,
        due_date: date | None = None,
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
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update_fields(self, task_id: UUID, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = datetime.now(UTC)
        await self.session.execute(
            sa_update(Task).where(Task.id == task_id).values(**fields)
        )

    async def update_status(self, task_id: UUID, status: str) -> None:
        await self.session.execute(
            sa_update(Task)
            .where(Task.id == task_id)
            .values(status=status, updated_at=datetime.now(UTC))
        )

    async def set_timer_disabled(self, task_id: UUID, disabled: bool) -> None:
        await self.session.execute(
            sa_update(Task)
            .where(Task.id == task_id)
            .values(timer_disabled=disabled, updated_at=datetime.now(UTC))
        )

    async def soft_delete(self, task_id: UUID) -> None:
        await self.session.execute(
            sa_update(Task)
            .where(Task.id == task_id)
            .values(deleted_at=datetime.now(UTC))
        )

    async def replace_assignees(
        self, task_id: UUID, *, assignee_ids: Sequence[UUID], assigned_by: UUID
    ) -> None:
        await self.session.execute(
            sa_delete(TaskAssignee).where(TaskAssignee.task_id == task_id)
        )
        for user_id in assignee_ids:
            self.session.add(
                TaskAssignee(task_id=task_id, user_id=user_id, assigned_by=assigned_by)
            )

    # ── Timer (ADR-03) ───────────────────────────────────────────────────
    # No existe timer_repository/timer_service todavía (E05, sprint siguiente).
    # Esta pieza mínima es necesaria SOLO para la regla ADR-03 de este sprint
    # (detener el timer al pasar de 1 a 2+ asignados). El CRUD completo de
    # timers (start/stop manual, endpoints) se construye en E05.

    async def get_active_timer(self, task_id: UUID) -> TaskTimeEntry | None:
        """Entrada de tiempo sin cerrar (stopped_at IS NULL) para la tarea."""
        result = await self.session.execute(
            select(TaskTimeEntry).where(
                TaskTimeEntry.task_id == task_id,
                TaskTimeEntry.stopped_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def stop_timer(self, entry: TaskTimeEntry, *, reason: str) -> None:
        now = datetime.now(UTC)
        duration = int((now - entry.started_at).total_seconds())
        await self.session.execute(
            sa_update(TaskTimeEntry)
            .where(TaskTimeEntry.id == entry.id)
            .values(stopped_at=now, duration_seconds=duration, stop_reason=reason)
        )
