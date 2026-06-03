"""Initial schema — Sprint 1

Revision ID: 0001
Revises: —
Create Date: 2025-01-01 00:00:00.000000

Crea todas las tablas del MVP incluyendo:
  · ENUMs: user_role, member_role (con 'owner' — DU-02), invitation_status,
           task_priority, task_status, mention_type
  · Tablas E01: users, email_verification_tokens, refresh_tokens, password_reset_tokens
  · Tabla de config: system_settings
  · Tablas E02/E03: project_members (role incluye 'owner' desde aquí — DU-02)
  · Tablas E04/E05/E07/E08: projects, tasks, task_assignees, task_time_entries,
                             task_comments, comment_mentions, audit_logs
  · Secuencia global task_number_seq (AG-05)
  · Índices críticos incluyendo GIN para FTS y constraint parcial para timer (ADR-03)
  · Triggers: updated_at, single_owner, timer_disabled
  · Datos iniciales: system_settings
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Extensiones ────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── ENUMs ──────────────────────────────────────────────────────────────────
    user_role = postgresql.ENUM(
        "viewer", "editor", "admin", name="user_role", create_type=True
    )
    user_role.create(op.get_bind())

    # DU-02: 'owner' incluido desde la migración inicial para evitar ALTER TYPE en Sprint 2
    member_role = postgresql.ENUM(
        "owner", "editor", "viewer", name="member_role", create_type=True
    )
    member_role.create(op.get_bind())

    invitation_status = postgresql.ENUM(
        "pending",
        "accepted",
        "rejected",
        "expired",
        name="invitation_status",
        create_type=True,
    )
    invitation_status.create(op.get_bind())

    task_priority = postgresql.ENUM(
        "low", "medium", "high", name="task_priority", create_type=True
    )
    task_priority.create(op.get_bind())

    task_status = postgresql.ENUM(
        "abierto", "en_proceso", "completo", name="task_status", create_type=True
    )
    task_status.create(op.get_bind())

    mention_type = postgresql.ENUM(
        "user", "task", name="mention_type", create_type=True
    )
    mention_type.create(op.get_bind())

    # ── Secuencia global para task_number (AG-05) ──────────────────────────────
    op.execute("CREATE SEQUENCE IF NOT EXISTS task_number_seq START 1")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.String(30), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(255), nullable=False, server_default="UTC"),
        sa.Column(
            "role",
            postgresql.ENUM(
                "viewer", "editor", "admin", name="user_role", create_type=False
            ),
            nullable=False,
            server_default="editor",
        ),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("username", name="users_username_uk"),
        sa.CheckConstraint(
            "LENGTH(username) BETWEEN 3 AND 30", name="users_username_len"
        ),
        sa.CheckConstraint("username ~ '^[a-zA-Z0-9_]+$'", name="users_username_alnum"),
    )
    op.create_index("users_email_uk", "users", [sa.text("LOWER(email)")], unique=True)
    op.create_index(
        "idx_users_deleted_at",
        "users",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── email_verification_tokens ──────────────────────────────────────────────
    op.create_table(
        "email_verification_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("token_hash", name="evt_token_hash_uk"),
    )
    op.create_index("idx_evt_user_id", "email_verification_tokens", ["user_id"])
    op.create_index(
        "idx_evt_expires_at",
        "email_verification_tokens",
        ["expires_at"],
        postgresql_where=sa.text("used = FALSE"),
    )

    # ── refresh_tokens (ADR-01) ────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("token_hash", name="rt_token_hash_uk"),
    )
    op.create_index("idx_rt_user_id", "refresh_tokens", ["user_id"])
    op.create_index(
        "idx_rt_active",
        "refresh_tokens",
        ["user_id"],
        postgresql_where=sa.text("is_revoked = FALSE"),
    )

    # ── password_reset_tokens ──────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("token_hash", name="prt_token_hash_uk"),
    )
    op.create_index("idx_prt_user_id", "password_reset_tokens", ["user_id"])

    # ── system_settings ────────────────────────────────────────────────────────
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.execute("""
        INSERT INTO system_settings (key, value, description) VALUES
        ('max_projects_per_user', '20',  'Máximo de proyectos que un usuario puede crear como owner'),
        ('max_timer_hours',        '12', 'Horas máximas de un timer activo antes del cierre automático'),
        ('invitation_expiry_days', '7',  'Días de vigencia de una invitación a proyecto'),
        ('max_task_assignees',     '10', 'Máximo de asignados por tarea')
    """)

    # ── projects ───────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("LENGTH(TRIM(name)) > 0", name="projects_name_not_empty"),
    )
    op.create_index("idx_projects_owner_id", "projects", ["owner_id"])
    op.create_index(
        "idx_projects_deleted_at",
        "projects",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── project_members (DU-02: member_role incluye 'owner') ──────────────────
    op.create_table(
        "project_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
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
                "owner", "editor", "viewer", name="member_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("removed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("removal_reason", sa.String(255), nullable=True),
        sa.UniqueConstraint("project_id", "user_id", name="pm_user_project_active_uk"),
    )
    op.create_index("idx_pm_project_id", "project_members", ["project_id"])
    op.create_index("idx_pm_user_id", "project_members", ["user_id"])
    op.create_index(
        "idx_pm_active",
        "project_members",
        ["project_id", "user_id"],
        postgresql_where=sa.text("removed_at IS NULL"),
    )

    # ── project_invitations ────────────────────────────────────────────────────
    op.create_table(
        "project_invitations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "owner", "editor", "viewer", name="member_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "accepted",
                "rejected",
                "expired",
                name="invitation_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("responded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("token_hash", name="pi_token_hash_uk"),
        sa.CheckConstraint("role <> 'owner'", name="pi_role_not_owner"),
    )
    op.create_index("idx_pi_project_id", "project_invitations", ["project_id"])

    # ── tasks ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_number",
            sa.Integer,
            nullable=False,
            server_default=sa.text("nextval('task_number_seq')"),
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "low", "medium", "high", name="task_priority", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "abierto",
                "en_proceso",
                "completo",
                name="task_status",
                create_type=False,
            ),
            nullable=False,
            server_default="abierto",
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("timer_disabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("task_number", name="tasks_task_number_uk"),
        sa.CheckConstraint("LENGTH(TRIM(title)) > 0", name="tasks_title_not_empty"),
        sa.CheckConstraint(
            "description IS NULL OR LENGTH(description) <= 2000",
            name="tasks_description_len",
        ),
    )
    # GIN index para Full Text Search (R-0404)
    op.execute("""
        ALTER TABLE tasks ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('spanish',
                    COALESCE(title, '') || ' ' || COALESCE(description, ''))
            ) STORED
    """)
    op.create_index(
        "idx_tasks_project_id",
        "tasks",
        ["project_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_tasks_status",
        "tasks",
        ["project_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.execute(
        "CREATE INDEX idx_tasks_search_vector ON tasks USING GIN (search_vector)"
    )

    # ── task_assignees ─────────────────────────────────────────────────────────
    op.create_table(
        "task_assignees",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("task_id", "user_id", name="ta_task_user_uk"),
    )
    op.create_index("idx_ta_task_id", "task_assignees", ["task_id"])
    op.create_index("idx_ta_user_id", "task_assignees", ["user_id"])

    # ── task_time_entries (ADR-03: constraint parcial 1 activo/usuario) ────────
    op.create_table(
        "task_time_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("stop_reason", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="tte_duration_positive",
        ),
        sa.CheckConstraint(
            "stopped_at IS NULL OR stopped_at >= started_at",
            name="tte_stopped_after_started",
        ),
    )
    # Constraint parcial: un solo timer activo por usuario (garantía a nivel DB)
    op.execute("""
        CREATE UNIQUE INDEX tte_one_active_per_user
        ON task_time_entries (user_id)
        WHERE stopped_at IS NULL
    """)
    op.create_index("idx_tte_task_id", "task_time_entries", ["task_id"])
    op.create_index("idx_tte_user_id", "task_time_entries", ["user_id"])
    op.create_index(
        "idx_tte_active",
        "task_time_entries",
        ["user_id"],
        postgresql_where=sa.text("stopped_at IS NULL"),
    )

    # ── task_comments ──────────────────────────────────────────────────────────
    op.create_table(
        "task_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("edited_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_tc_task_id",
        "task_comments",
        ["task_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── comment_mentions (ADR-02: solo visual en MVP) ─────────────────────────
    op.create_table(
        "comment_mentions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "comment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("task_comments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mention_type",
            postgresql.ENUM("user", "task", name="mention_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "mentioned_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "mentioned_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            """(mention_type = 'user' AND mentioned_user_id IS NOT NULL AND mentioned_task_id IS NULL)
               OR (mention_type = 'task' AND mentioned_task_id IS NOT NULL AND mentioned_user_id IS NULL)""",
            name="cm_user_xor_task",
        ),
    )
    op.create_index("idx_cm_comment_id", "comment_mentions", ["comment_id"])

    # ── audit_logs (E08) ───────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_al_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_al_action", "audit_logs", ["action"])
    op.create_index("idx_al_created_at", "audit_logs", [sa.text("created_at DESC")])
    op.execute(
        "CREATE INDEX idx_al_created_at_brin ON audit_logs USING BRIN (created_at)"
    )

    # ── Trigger: updated_at automático ─────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$
    """)
    for table in ("users", "projects", "tasks"):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()
        """)

    # ── Trigger: único owner por proyecto (DU-02) ──────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_validate_single_owner()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.role = 'owner' THEN
                IF EXISTS (
                    SELECT 1 FROM project_members
                    WHERE project_id = NEW.project_id
                      AND role = 'owner'
                      AND removed_at IS NULL
                      AND id <> NEW.id
                ) THEN
                    RAISE EXCEPTION 'Ya existe un owner activo en el proyecto. Solo puede haber uno (DU-02).';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_validate_single_owner
            BEFORE INSERT OR UPDATE ON project_members
            FOR EACH ROW EXECUTE FUNCTION fn_validate_single_owner()
    """)

    # ── Trigger: timer_disabled automático (ADR-03) ────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_update_timer_disabled()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            v_task_id UUID;
            v_count   INTEGER;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                v_task_id := OLD.task_id;
            ELSE
                v_task_id := NEW.task_id;
            END IF;
            SELECT COUNT(*) INTO v_count
            FROM task_assignees ta
            JOIN tasks t ON t.id = ta.task_id
            JOIN project_members pm ON pm.project_id = t.project_id
                                    AND pm.user_id = ta.user_id
                                    AND pm.removed_at IS NULL
            WHERE ta.task_id = v_task_id;
            UPDATE tasks
            SET timer_disabled = (v_count >= 2),
                updated_at     = NOW()
            WHERE id = v_task_id;
            RETURN COALESCE(NEW, OLD);
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_task_assignees_timer_disabled
            AFTER INSERT OR DELETE ON task_assignees
            FOR EACH ROW EXECUTE FUNCTION fn_update_timer_disabled()
    """)


def downgrade() -> None:
    # Triggers y funciones
    for table in ("users", "projects", "tasks"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.execute("DROP TRIGGER IF EXISTS trg_validate_single_owner ON project_members")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_task_assignees_timer_disabled ON task_assignees"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS fn_validate_single_owner()")
    op.execute("DROP FUNCTION IF EXISTS fn_update_timer_disabled()")

    # Tablas en orden inverso de dependencias
    for table in [
        "comment_mentions",
        "task_comments",
        "task_time_entries",
        "task_assignees",
        "tasks",
        "project_invitations",
        "project_members",
        "projects",
        "system_settings",
        "password_reset_tokens",
        "refresh_tokens",
        "email_verification_tokens",
        "audit_logs",
        "users",
    ]:
        op.drop_table(table)

    # Secuencia
    op.execute("DROP SEQUENCE IF EXISTS task_number_seq")

    # ENUMs
    for enum in [
        "mention_type",
        "task_status",
        "task_priority",
        "invitation_status",
        "member_role",
        "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
