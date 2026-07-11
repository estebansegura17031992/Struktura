"""DTOs (request/response) de `tasks` — Entrega PM: Backend Día 2 (E04).

Contrato congelado para desbloquear a Frontend. Las rutas que consumen estos
schemas están registradas como stub en `app/routers/tasks.py` únicamente para
que aparezcan en OpenAPI/Swagger; la lógica real se implementa en Día 3.

Ubicación en el repo: backend/app/schemas/task.py

ASUNCIÓN A VALIDAR CON PM/UX (no bloquea el contrato, pero Frontend debe saberlo):
  La tabla `users` (kanban_mvp_erd.html) NO tiene columna `avatar`. Ese campo
  se expone en el DTO como Optional[str] y por ahora se resuelve en el service
  layer (Día 3) con un placeholder (ej. Gravatar por hash de email) hasta que
  Producto defina si se agrega una columna real `avatar_url` a `users` en una
  migración futura. `is_active` de cada assignee se deriva de `users.deleted_at
  IS NULL` (no es una columna nueva).
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --------------------------------------------------------------------------
# Enums (deben coincidir 1:1 con los ENUM de PostgreSQL creados en Día 1)
# --------------------------------------------------------------------------
class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskStatus(str, Enum):
    abierto = "abierto"
    en_proceso = "en_proceso"
    completo = "completo"


# --------------------------------------------------------------------------
# Sub-objeto: assignee dentro de una tarea
# --------------------------------------------------------------------------
class TaskAssigneeOut(BaseModel):
    """Representa a un usuario asignado, tal como lo consume Frontend en la tarjeta Kanban."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="ID del usuario asignado (users.id)")
    username: str = Field(..., examples=["mgomez"])
    avatar: Optional[str] = Field(
        default=None,
        description="URL del avatar. Nullable hasta que Producto defina el origen (ver nota de asunción arriba).",
    )
    is_active: bool = Field(
        ..., description="False si la cuenta del usuario asignado tiene soft-delete (users.deleted_at)."
    )


# --------------------------------------------------------------------------
# Request DTOs
# --------------------------------------------------------------------------
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: TaskPriority
    project_id: UUID
    due_date: Optional[date] = None
    timer_disabled: bool = Field(
        default=False, description="ADR-03. Si el proyecto no usa cronómetro para esta tarea."
    )
    assignee_ids: List[UUID] = Field(
        default_factory=list,
        description="IDs de usuarios a asignar al crear la tarea. Validado contra "
        "system_settings.max_task_assignees (=5) en el service layer (Día 3).",
    )

    @field_validator("assignee_ids")
    @classmethod
    def _dedupe_assignees(cls, v: List[UUID]) -> List[UUID]:
        return list(dict.fromkeys(v))


class TaskUpdate(BaseModel):
    """PATCH /tasks/{id} — todos los campos opcionales (actualización parcial)."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    timer_disabled: Optional[bool] = None
    assignee_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Si se envía, reemplaza el set completo de asignados (máx. system_settings.max_task_assignees).",
    )


class TaskStatusUpdate(BaseModel):
    """PATCH /tasks/{id}/status — único campo editable en este endpoint (AG y RBAC especiales)."""

    status: TaskStatus


class TaskAssigneesUpdate(BaseModel):
    """PATCH /tasks/{id}/assignees — reemplaza el set completo de asignados (R-0407).
    Mínimo 1 asignado (no se permite dejar la tarea sin nadie). Máximo:
    system_settings.max_task_assignees, validado en el service layer."""

    assignee_ids: List[UUID] = Field(..., min_length=1)

    @field_validator("assignee_ids")
    @classmethod
    def _dedupe(cls, v: List[UUID]) -> List[UUID]:
        deduped = list(dict.fromkeys(v))
        if not deduped:
            raise ValueError("Debe haber al menos un asignado.")
        return deduped


# --------------------------------------------------------------------------
# Response DTO
# --------------------------------------------------------------------------
class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_number: int = Field(..., description="SERIAL global, visible en UI como identificador corto (AG-05).")
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    status: TaskStatus
    project_id: UUID
    created_by: UUID
    due_date: Optional[date] = None
    timer_disabled: bool
    assignees: List[TaskAssigneeOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TaskListItem(TaskOut):
    """Variante liviana para listados/tablero Kanban (mismo shape por ahora; separado
    para poder recortar campos en el futuro sin romper el detalle de tarea)."""

    pass


class PaginatedTasks(BaseModel):
    """Sigue el wrapper estándar de paginación ya definido en R-0901."""

    items: List[TaskListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
    next_page: Optional[int] = None
    previous_page: Optional[int] = None