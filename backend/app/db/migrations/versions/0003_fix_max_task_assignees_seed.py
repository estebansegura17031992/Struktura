"""E04 - Corrige system_settings.max_task_assignees de 10 a 5

Entrega PM: Backend Día 1 (E04).

CONTEXTO (importante, no repetir el error): `0001_initial_schema.py` YA
crea las tablas `tasks` y `task_assignees`, los ENUM `task_priority` /
`task_status`, la secuencia `task_number_seq`, la columna generada
`search_vector` y su índice GIN (`idx_tasks_search_vector`). Todo eso
está fuera del alcance de esta migración — NO se vuelve a crear nada de
eso aquí, solo se corrige el valor del seed.

`0001` insertó `system_settings.max_task_assignees = '10'`
(línea 251 de `0001_initial_schema.py`). El PM pidió explícitamente
`max_task_assignees = 5`. Esta migración es un UPDATE correctivo, no un
INSERT (la fila ya existe).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-01
"""
from alembic import op

# --- Alembic identifiers -----------------------------------------------
revision: str = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

OLD_VALUE = "10"
NEW_VALUE = "5"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE system_settings
        SET value = '{NEW_VALUE}', updated_at = now()
        WHERE key = 'max_task_assignees';
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE system_settings
        SET value = '{OLD_VALUE}', updated_at = now()
        WHERE key = 'max_task_assignees';
        """
    )