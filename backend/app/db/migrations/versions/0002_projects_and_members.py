"""
Migracion S2 - marcador de sprint para projects y project_members
Sprint 2 - E03 - ART-08 - R-0301 - R-0302

Las tablas projects, project_members y project_invitations fueron
creadas en la migracion 0001 del Sprint 1 por diseno (DU-02).
Esta migracion es un marcador formal del Sprint 2 en el historial
de Alembic. No ejecuta DDL adicional.
"""

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
