"""
Schemas Pydantic — Proyectos y membresías
Sprint 2 · E03 · DTOs de request y response

Separación estricta entre schemas de entrada (Create/Update) y salida (Response).
Los IDs siempre como str en el response para compatibilidad JSON.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.project import ProjectMember

# ── Request schemas ────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del proyecto"
    )
    description: str | None = Field(
        None, max_length=500, description="Descripción opcional"
    )

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío.")
        return v.strip()


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío.")
        return v.strip() if v else v


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: str = Field(
        default="viewer",
        description="Rol del nuevo miembro en el proyecto: owner | editor | viewer",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"owner", "editor", "viewer"}
        if v not in allowed:
            raise ValueError(f"Rol inválido. Permitidos: {', '.join(sorted(allowed))}")
        return v


class TransferOwnershipRequest(BaseModel):
    new_owner_id: uuid.UUID = Field(
        ..., description="ID del nuevo owner (debe ser miembro activo)"
    )


# ── Response schemas ───────────────────────────────────────────────────────────


class MemberUserResponse(BaseModel):
    """Datos del usuario dentro de una membresía (sin datos sensibles)."""

    id: str
    username: str
    full_name: str | None
    role: str  # Rol global del sistema

    model_config = {"from_attributes": True}


class ProjectMemberResponse(BaseModel):
    """
    DTO de membresía para responses.
    is_active es clave para el badge "Miembro removido" en el frontend (DU-01).
    """

    id: str
    project_id: str
    user_id: str
    role: str
    joined_at: datetime
    removed_at: datetime | None
    is_active: bool
    user: MemberUserResponse | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_user(cls, member: ProjectMember) -> "ProjectMemberResponse":
        return cls(
            id=str(member.id),
            project_id=str(member.project_id),
            user_id=str(member.user_id),
            role=member.role,
            joined_at=member.joined_at,
            removed_at=member.removed_at,
            is_active=member.removed_at is None,
            user=MemberUserResponse(
                id=str(member.user.id),
                username=member.user.username,
                full_name=member.user.full_name,
                role=member.user.role,
            )
            if hasattr(member, "user") and member.user is not None
            else None,
        )


class ProjectResponse(BaseModel):
    """DTO de proyecto para responses."""

    id: str
    name: str
    description: str | None
    owner_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    member_count: int | None = None  # Calculado en el service si se pide

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(
        cls, project: object, member_count: int | None = None
    ) -> "ProjectResponse":
        return cls(
            id=str(project.id),  # type: ignore[attr-defined]
            name=project.name,  # type: ignore[attr-defined]
            description=project.description,  # type: ignore[attr-defined]
            owner_id=str(project.owner_id),  # type: ignore[attr-defined]
            created_at=project.created_at,  # type: ignore[attr-defined]
            updated_at=project.updated_at,  # type: ignore[attr-defined]
            deleted_at=project.deleted_at,  # type: ignore[attr-defined]
            member_count=member_count,
        )


class ProjectListResponse(BaseModel):
    """Response paginado de proyectos (wrapper estándar del proyecto)."""

    items: list[ProjectResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
    next_page: int | None
    previous_page: int | None


class OwnershipTransferResponse(BaseModel):
    """Response de transferencia de ownership."""

    previous_owner: ProjectMemberResponse
    new_owner: ProjectMemberResponse
    message: str = "Ownership transferido exitosamente."
