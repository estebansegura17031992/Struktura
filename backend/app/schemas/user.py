"""Schemas de usuario — request/response DTOs (R-0101, R-0108)."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    timezone: str = "UTC"  # detectado automáticamente por el frontend (AG-02)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not 3 <= len(v) <= 30:
            raise ValueError("El username debe tener entre 3 y 30 caracteres")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "El username solo puede contener letras, números y guiones bajos"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None
    timezone: str
    role: str
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    timezone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v
