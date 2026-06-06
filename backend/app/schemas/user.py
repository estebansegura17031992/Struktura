"""Schemas de usuario — request/response DTOs (R-0101, R-0108, R-0204)."""
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Auth / registro ────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    timezone: str = "UTC"           # detectado automáticamente por el frontend (AG-02)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not 3 <= len(v) <= 30:
            raise ValueError("El username debe tener entre 3 y 30 caracteres")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("El username solo puede contener letras, números y guiones bajos")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v


# ── Perfil de usuario ──────────────────────────────────────────────────────────

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


# ── Admin schemas (Sprint 2 · ART-04 · R-0204) ────────────────────────────────

class ChangeRoleRequest(BaseModel):
    """Body para PATCH /admin/users/{id}/role"""
    role: str = Field(..., description="Nuevo rol: viewer | editor | admin")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"viewer", "editor", "admin"}
        if v not in allowed:
            raise ValueError(f"Rol inválido. Permitidos: {', '.join(sorted(allowed))}")
        return v


class UserAdminResponse(BaseModel):
    """DTO de usuario para el panel de administración."""
    id: str
    email: str
    username: str
    full_name: str | None
    role: str
    is_verified: bool
    is_active: bool
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, user: object) -> "UserAdminResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_verified=user.is_verified,
            is_active=user.is_active,
            timezone=user.timezone,
            created_at=user.created_at,
        )


class UserListResponse(BaseModel):
    """Response paginado para listado de usuarios (admin)."""
    items: list[UserAdminResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
    next_page: int | None
    previous_page: int | None
