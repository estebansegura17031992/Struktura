"""DTOs de cronómetro (E05 · Sprint 4 · Objetivos 1, 2, 3).

Ubicación en el repo: backend/app/schemas/timer.py
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TimerEntryOut(BaseModel):
    """Una entrada de `task_time_entries`, activa o cerrada."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    user_id: UUID
    started_at: datetime
    stopped_at: datetime | None = None
    duration_seconds: int | None = None
    stop_reason: str | None = None


class ActiveTimerOut(BaseModel):
    """GET /timers/active — Objetivo 2. `elapsed_seconds` calculado al consultar,
    no persistido (el timer sigue corriendo)."""

    id: UUID
    task_id: UUID
    started_at: datetime
    elapsed_seconds: int


class TimeEntriesResponse(BaseModel):
    """GET /tasks/{id}/time-entries — Objetivo 3. `scope` indica si el listado
    es solo del usuario (viewer, DU-04) o de todo el equipo (editor/admin)."""

    scope: str  # "own" | "all"
    items: list[TimerEntryOut]
