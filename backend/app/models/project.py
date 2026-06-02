"""
Models: Project, ProjectMember
Sprint 2 · E03 · R-0301 a R-0306
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class ProjectMemberRole(str, enum.Enum):
    """
    Rol de un usuario dentro de un proyecto específico.
    Independiente del rol global del sistema (users.role).
    Regla de precedencia: se aplica el rol más restrictivo entre sistema y proyecto.
    """
    owner = "owner"    # Control total + transferencia de ownership (DU-02)
    editor = "editor"  # CRUD tareas y miembros dentro del proyecto
    viewer = "viewer"  # Solo lectura dentro del proyecto


# ── Project ───────────────────────────────────────────────────────────────────

class Project(Base):
    """
    Tabla: projects
    Soft delete via deleted_at. Proyectos eliminados no aparecen en ningún listado.
    El creador queda automáticamente como owner en project_members (service layer).
    Límite de proyectos por usuario en system_settings.max_projects_per_user (default 20).
    """
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # FK al usuario owner (denormalizado para queries rápidas de ownership).
    # La fuente de verdad del owner es project_members.role = 'owner'.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Soft delete (AG-04). NULL = activo. IS NOT NULL = eliminado.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[owner_id],
        lazy="select",
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_deleted_at", "deleted_at"),
        # Índice parcial: solo proyectos activos — optimiza el listado principal
        Index(
            "ix_projects_active",
            "owner_id",
            "created_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} deleted={self.deleted_at is not None}>"


# ── ProjectMember ─────────────────────────────────────────────────────────────

class ProjectMember(Base):
    """
    Tabla: project_members
    Relación M:N entre usuarios y proyectos con rol de proyecto.
    Soft delete via removed_at — los registros históricos se conservan (R-0303).
    Solo puede existir UN owner por proyecto (validado en service layer).

    is_active (property): True si removed_at IS NULL
    El DTO de tarea incluye is_active por asignado para badge "Miembro removido" (DU-01).
    """
    __tablename__ = "project_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ENUM definido en migración Alembic: owner | editor | viewer
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(ProjectMemberRole, name="project_member_role", create_type=False),
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Soft delete de membresía (R-0303). NULL = activo. IS NOT NULL = removido.
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        lazy="select",
    )

    # ── Indexes & Constraints ─────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_project_members_project_id", "project_id"),
        Index("ix_project_members_user_id", "user_id"),
        # Índice parcial: miembros activos (los más consultados)
        Index(
            "ix_project_members_active",
            "project_id",
            "user_id",
            postgresql_where="removed_at IS NULL",
        ),
        # Un usuario solo puede tener UNA membresía activa por proyecto.
        # Re-invitar crea una nueva fila (la anterior queda con removed_at).
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_members_active",
            # Nota: la unicidad sobre activos se maneja en service layer
            # porque PostgreSQL no soporta UNIQUE parcial con ORM fácilmente.
        ),
    )

    @property
    def is_active(self) -> bool:
        """True si la membresía está activa (removed_at IS NULL)."""
        return self.removed_at is None

    def __repr__(self) -> str:
        return (
            f"<ProjectMember project={self.project_id} "
            f"user={self.user_id} role={self.role} active={self.is_active}>"
        )