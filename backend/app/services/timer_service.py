"""Service de cronómetro — E05 · Sprint 4 (Objetivos 1, 2, 3, 4, 6).

Sin lógica de permisos/RBAC — vive en los endpoints, mismo patrón que
`TaskService`.

Ubicación en el repo: backend/app/services/timer_service.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppBaseError
from app.repositories.task_repository import TaskRepository
from app.repositories.timer_repository import TimerRepository
from app.schemas.timer import ActiveTimerOut, TimeEntriesResponse, TimerEntryOut
from app.services.audit_service import log_action

DEFAULT_MAX_TIMER_HOURS = 12
DELETE_WINDOW_HOURS = 24


async def _get_max_timer_hours(session: AsyncSession) -> int:
    """Lee system_settings.max_timer_hours (sembrada en la migración 0001, =12)."""
    result = await session.execute(
        text("SELECT value FROM system_settings WHERE key = 'max_timer_hours'")
    )
    row = result.first()
    if row is None:
        return DEFAULT_MAX_TIMER_HOURS
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return DEFAULT_MAX_TIMER_HOURS


class TimerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TimerRepository(session)
        self._task_repo = TaskRepository(session)

    # ── Objetivo 1 ───────────────────────────────────────────────────────

    async def start(self, *, task_id: UUID, actor_id: UUID) -> TimerEntryOut:
        task = await self._task_repo.get_active(task_id)
        if task is None:
            raise AppBaseError("NOT_FOUND", "Tarea no encontrada.", 404)

        assignees = await self._task_repo.get_assignees_with_user(task_id)
        assignee_ids = {a.user_id for a, _u in assignees}
        if actor_id not in assignee_ids:
            raise AppBaseError(
                "NOT_ASSIGNED",
                "Solo un usuario asignado a la tarea puede iniciar el cronómetro.",
                403,
            )
        if len(assignee_ids) != 1:
            raise AppBaseError(
                "TIMER_MULTI_ASSIGNEE_DISABLED",
                "El cronómetro está deshabilitado en tareas con más de un "
                "asignado (ADR-03).",
                422,
            )

        # Un usuario nunca tiene dos timers activos — se detiene el anterior
        # (de cualquier tarea) antes de abrir el nuevo. FOR UPDATE en el
        # repo serializa esto contra otro start/stop concurrente del mismo
        # usuario; el índice único parcial en DB cubre el caso de una race
        # genuina donde ninguno ve entrada previa (ver TimerRepository.create).
        previous = await self._repo.get_active_for_user(actor_id)
        if previous is not None and previous.task_id != task_id:
            await self._repo.close(previous, reason="new_timer_started")
            await log_action(
                self._session,
                action="timer_auto_stopped_new_start",
                user_id=actor_id,
                entity_type="task_time_entry",
                entity_id=previous.id,
                metadata={
                    "previous_task_id": str(previous.task_id),
                    "new_task_id": str(task_id),
                },
            )
        elif previous is not None and previous.task_id == task_id:
            # Ya hay un timer activo en ESTA misma tarea — idempotente, no
            # crear uno nuevo (evita 2 entradas activas del mismo usuario).
            raise AppBaseError(
                "TIMER_ALREADY_ACTIVE",
                "Ya tienes un cronómetro activo en esta tarea.",
                409,
            )

        try:
            entry = await self._repo.create(task_id=task_id, user_id=actor_id)
        except IntegrityError as exc:
            # Race genuina: dos starts concurrentes sin entrada previa visible.
            # El índice único parcial (tte_one_active_per_user) rechazó este.
            await self._session.rollback()
            raise AppBaseError(
                "TIMER_ALREADY_ACTIVE",
                "Ya tienes un cronómetro activo. Actualiza para ver el estado real.",
                409,
            ) from exc

        await log_action(
            self._session,
            action="timer_started",
            user_id=actor_id,
            entity_type="task_time_entry",
            entity_id=entry.id,
            metadata={"task_id": str(task_id)},
        )
        await self._session.commit()
        return TimerEntryOut.model_validate(entry)

    async def stop(self, *, task_id: UUID, actor_id: UUID) -> TimerEntryOut:
        """Solo el dueño del timer puede detenerlo (admin usa `stop_for_user`,
        Objetivo 6, que no requiere ser el dueño)."""
        entry = await self._repo.get_active_for_user(actor_id)
        if entry is None or entry.task_id != task_id:
            raise AppBaseError(
                "NOT_FOUND", "No tienes un cronómetro activo en esta tarea.", 404
            )

        await self._repo.close(entry, reason="manual_stop")
        await log_action(
            self._session,
            action="timer_stopped",
            user_id=actor_id,
            entity_type="task_time_entry",
            entity_id=entry.id,
            metadata={"task_id": str(task_id)},
        )
        await self._session.commit()
        await self._session.refresh(entry)
        return TimerEntryOut.model_validate(entry)

    # ── Objetivo 2 ───────────────────────────────────────────────────────

    async def get_active(self, *, user_id: UUID) -> ActiveTimerOut | None:
        entry = await self._repo.get_active_for_user(user_id)
        if entry is None:
            return None
        elapsed = int((datetime.now(UTC) - entry.started_at).total_seconds())
        return ActiveTimerOut(
            id=entry.id,
            task_id=entry.task_id,
            started_at=entry.started_at,
            elapsed_seconds=elapsed,
        )

    # ── Objetivo 3 ───────────────────────────────────────────────────────

    async def list_time_entries(
        self, *, task_id: UUID, requester_id: UUID, is_privileged: bool
    ) -> TimeEntriesResponse:
        """DU-04: viewer solo ve las suyas (scope="own"); editor/admin ven
        las de todo el equipo (scope="all")."""
        scope = "all" if is_privileged else "own"
        user_filter = None if is_privileged else requester_id
        entries = await self._repo.list_stopped_for_task(task_id, user_id=user_filter)
        return TimeEntriesResponse(
            scope=scope, items=[TimerEntryOut.model_validate(e) for e in entries]
        )

    async def delete_entry(
        self, *, entry_id: UUID, actor_id: UUID, actor_is_admin: bool
    ) -> None:
        entry = await self._repo.get_by_id(entry_id)
        if entry is None:
            raise AppBaseError("NOT_FOUND", "Entrada de tiempo no encontrada.", 404)

        if not actor_is_admin:
            if entry.user_id != actor_id:
                raise AppBaseError(
                    "INSUFFICIENT_PERMISSIONS",
                    "Solo puedes borrar tus propias entradas de tiempo.",
                    403,
                )
            if entry.stopped_at is None:
                raise AppBaseError(
                    "VALIDATION_ERROR", "No se puede borrar un timer activo.", 422
                )
            age_seconds = (datetime.now(UTC) - entry.stopped_at).total_seconds()
            if age_seconds > DELETE_WINDOW_HOURS * 3600:
                raise AppBaseError(
                    "ENTRY_TOO_OLD",
                    f"Solo puedes borrar entradas de las últimas "
                    f"{DELETE_WINDOW_HOURS} horas.",
                    422,
                )

        was_owner = entry.user_id == actor_id
        await self._repo.delete(entry_id)
        await log_action(
            self._session,
            action="time_entry_deleted",
            user_id=actor_id,
            entity_type="task_time_entry",
            entity_id=entry_id,
            metadata={"task_id": str(entry.task_id), "was_owner": was_owner},
        )
        await self._session.commit()

    # ── Objetivo 4 (job de huérfanos) ────────────────────────────────────

    async def close_orphaned_timers(self) -> int:
        """Cierra timers activos más viejos que system_settings.max_timer_hours
        (default 12). La duración se calcula HASTA EL LÍMITE, no hasta el
        momento del cierre — un timer que corrió 3 días no factura 3 días.

        DECISIÓN DE PM PENDIENTE (ver Objetivo 4 del spec de sprint): qué le
        llega al frontend cuando esto pasa mientras el usuario cree que el
        timer sigue corriendo. No implementado acá — solo el cierre y el
        audit log, que no dependen de esa decisión.
        """
        max_hours = await _get_max_timer_hours(self._session)
        cutoff = datetime.now(UTC) - timedelta(hours=max_hours)
        orphaned = await self._repo.list_orphaned(older_than=cutoff)

        for entry in orphaned:
            limit_time = entry.started_at + timedelta(hours=max_hours)
            await self._repo.close(entry, reason="auto_closed_max_hours", at=limit_time)
            await log_action(
                self._session,
                action="timer_auto_closed",
                user_id=entry.user_id,
                entity_type="task_time_entry",
                entity_id=entry.id,
                metadata={
                    "task_id": str(entry.task_id),
                    "max_timer_hours": max_hours,
                    "started_at": entry.started_at.isoformat(),
                },
            )

        if orphaned:
            await self._session.commit()
        return len(orphaned)

    # ── Objetivo 5 (logout) y 6 (admin) ──────────────────────────────────
    # Viven en AuthService.logout (atómico con el resto del logout) y en el
    # endpoint de admin respectivamente — ambos llaman a TimerRepository
    # directo para no romper la atomicidad de su propia transacción.
