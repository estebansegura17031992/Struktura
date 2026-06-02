"""
Migración S2 — tablas projects y project_members
Sprint 2 · E03 · ART-08 · R-0301 · R-0302

Precondición: migración 0001_initial_schema debe estar aplicada.
El ENUM project_member_role (owner|editor|viewer) ya existe desde la migración
inicial del S1. Esta migración solo crea las tablas que lo usan.

Para verificar antes de aplicar:
  SELECT EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'project_member_role'
  );
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revisión generada por Alembic
revision = "0002_projects_and_members"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Verificar / crear ENUM si no existe ────────────────────────────────
    # El ENUM debería existir desde la migración 0001. Si por alguna razón
    # no existe (entorno nuevo), lo creamos aquí de forma idempotente.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'project_member_role'
            ) THEN
                CREATE TYPE project_member_role AS ENUM ('owner', 'editor', 'viewer');
            END IF;
        END
        $$;
    """)

    # ── 2. Tabla projects ─────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Índices en projects
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"])
    # Índice parcial para listado de proyectos activos (query más frecuente)
    op.execute("""
        CREATE INDEX ix_projects_active
        ON projects (owner_id, created_at)
        WHERE deleted_at IS NULL;
    """)

    # Trigger para updated_at automático
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    op.execute("""
        CREATE TRIGGER projects_updated_at
        BEFORE UPDATE ON projects
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ── 3. Tabla project_members ──────────────────────────────────────────────
    op.create_table(
        "project_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(
                "owner", "editor", "viewer",
                name="project_member_role",
                create_type=False,  # Ya existe desde 0001
            ),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "removed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Índices en project_members
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    # Índice parcial para membresías activas (query más frecuente en verify_project_membership)
    op.execute("""
        CREATE INDEX ix_project_members_active
        ON project_members (project_id, user_id)
        WHERE removed_at IS NULL;
    """)
    # Unicidad activa: un usuario no puede tener dos membresías activas en el mismo proyecto
    op.execute("""
        CREATE UNIQUE INDEX uq_project_members_active_unique
        ON project_members (project_id, user_id)
        WHERE removed_at IS NULL;
    """)


def downgrade() -> None:
    # Eliminar en orden inverso respetando FKs
    op.execute("DROP TRIGGER IF EXISTS projects_updated_at ON projects;")
    op.drop_table("project_members")
    op.drop_table("projects")
    # No eliminar el ENUM — puede ser usado por otras migraciones futuras (E04 tasks)
    # Si se quiere eliminar: op.execute("DROP TYPE IF EXISTS project_member_role;")