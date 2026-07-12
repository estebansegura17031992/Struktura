"""Repository de cronómetro (`task_time_entries`) — E05 · Sprint 4.

`app/repositories/task_repository.py` ya tenía 2 métodos mínimos
(`get_active_timer`/`stop_timer`, con scope por `task_id`) agregados
SOLO para la regla ADR-03 de E04 (detener timer al pasar a 2+ asignados).
Esos NO se tocan acá — siguen sirviendo a ese único caso.

Este repo es el CRUD completo de timers con scope por `user_id` (un
usuario nunca tiene dos timers activos, sin importar la tarea), que
CLAUDE.md dejó anotado como pendiente de decidir "al construir E05".
Se decidió migrar: repo dedicado en vez de seguir agregando métodos de
timer a TaskRepository.

Ubicación en el repo: backend/app/repositories/timer_repository.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskTimeEntry


class TimerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_for_user(self, user_id: UUID) -> TaskTimeEntry | None:
        """Entrada activa (stopped_at IS NULL) del usuario, sin importar la
        tarea. `FOR UPDATE` serializa contra otro `start`/`stop` concurrente
        del mismo usuario en la misma transacción."""
        result = await self.session.execute(
            select(TaskTimeEntry)
            .where(TaskTimeEntry.user_id == user_id, TaskTimeEntry.stopped_at.is_(None))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, entry_id: UUID) -> TaskTimeEntry | None:
        result = await self.session.execute(
            select(TaskTimeEntry).where(TaskTimeEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def create(self, *, task_id: UUID, user_id: UUID) -> TaskTimeEntry:
        """El índice único parcial `tte_one_active_per_user` (migración 0001)
        es la garantía real contra dos timers activos del mismo usuario en
        una race genuina — si dos requests concurrentes llegan sin ver una
        entrada previa (ninguna existía), el segundo INSERT falla acá con
        IntegrityError; el service lo traduce a un error de dominio."""
        entry = TaskTimeEntry(
            task_id=task_id, user_id=user_id, started_at=datetime.now(UTC)
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def close(
        self, entry: TaskTimeEntry, *, reason: str, at: datetime | None = None
    ) -> None:
        stopped_at = at or datetime.now(UTC)
        duration = int((stopped_at - entry.started_at).total_seconds())
        await self.session.execute(
            sa_update(TaskTimeEntry)
            .where(TaskTimeEntry.id == entry.id)
            .values(
                stopped_at=stopped_at, duration_seconds=duration, stop_reason=reason
            )
        )

    async def list_stopped_for_task(
        self, task_id: UUID, *, user_id: UUID | None = None
    ) -> list[TaskTimeEntry]:
        """Historial de tiempo — Objetivo 3. Solo entradas cerradas
        (stopped_at IS NOT NULL). `user_id` filtra el scope "own" (viewer)."""
        stmt = select(TaskTimeEntry).where(
            TaskTimeEntry.task_id == task_id, TaskTimeEntry.stopped_at.is_not(None)
        )
        if user_id is not None:
            stmt = stmt.where(TaskTimeEntry.user_id == user_id)
        result = await self.session.execute(
            stmt.order_by(TaskTimeEntry.started_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, entry_id: UUID) -> None:
        await self.session.execute(
            sa_delete(TaskTimeEntry).where(TaskTimeEntry.id == entry_id)
        )

    async def list_orphaned(self, *, older_than: datetime) -> list[TaskTimeEntry]:
        """Timers activos iniciados antes de `older_than` — Objetivo 4 (job
        de huérfanos). No importa cuándo se consulta, solo cuándo empezaron."""
        result = await self.session.execute(
            select(TaskTimeEntry).where(
                TaskTimeEntry.stopped_at.is_(None),
                TaskTimeEntry.started_at < older_than,
            )
        )
        return list(result.scalars().all())
