"""
Migración S2 — marcador de sprint para projects y project_members
Sprint 2 · E03 · ART-08 · R-0301 · R-0302
 
NOTA: Las tablas projects, project_members y project_invitations,
junto con todos sus ENUMs (member_role, invitation_status), índices
y triggers (fn_validate_single_owner, trg_validate_single_owner),
fueron creadas en la migración 0001_initial_schema del Sprint 1
por diseño (DU-02 — el ENUM member_role incluye 'owner' desde el inicio).
 
Esta migración existe como marcador formal del Sprint 2 en el historial
de Alembic. No ejecuta DDL adicional.
"""
 
from alembic import op
 
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None
 
 
def upgrade() -> None:
    # Las tablas projects, project_members y project_invitations
    # ya existen desde la migración 0001. Sin DDL adicional.
    pass
 
 
def downgrade() -> None:
    # Sin DDL que revertir — las tablas las maneja 0001.
    pass
