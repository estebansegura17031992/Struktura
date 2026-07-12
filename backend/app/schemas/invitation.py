"""DTOs de invitaciones a proyecto (E03 · Sprint 4 · Objetivos 7, 8, 9).

`app/models/project.py::ProjectInvitation` y la tabla `project_invitations`
ya existían (migración 0001, Sprint 1 — DU-02) pero sin repository/service/
endpoints wireados. Este archivo es la contraparte de DTOs.

Ubicación en el repo: backend/app/schemas/invitation.py
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(..., description="viewer o editor — nunca owner")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"viewer", "editor"}:
            raise ValueError("Rol inválido para invitación. Permitidos: viewer, editor")
        return v


class InvitationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    email: str
    role: str
    status: str
    invited_by: UUID
    expires_at: datetime
    responded_at: datetime | None = None
    created_at: datetime
