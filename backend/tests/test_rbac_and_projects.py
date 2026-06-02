"""
Tests de integración — Sprint 2 · E02/E03 · Día 1
ART-07 (migración) · ART-01 (require_role) · ART-02 (verify_project_membership)

Cobertura objetivo:
  - require_role: happy path + rol insuficiente + token inválido
  - verify_project_membership: activo + sin membresía + removido + admin bypass
  - Migración: tablas existen con columnas correctas

Para ejecutar:
  pytest tests/integration/test_rbac_and_projects.py -v --tb=short
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text

from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db_session) -> User:
    """Usuario con rol admin."""
    return await create_test_user(db_session, role="admin", username="admin_test")


@pytest_asyncio.fixture
async def editor_user(db_session) -> User:
    """Usuario con rol editor."""
    return await create_test_user(db_session, role="editor", username="editor_test")


@pytest_asyncio.fixture
async def viewer_user(db_session) -> User:
    """Usuario con rol viewer."""
    return await create_test_user(db_session, role="viewer", username="viewer_test")


@pytest_asyncio.fixture
async def project_with_owner(db_session, editor_user) -> dict:
    """Proyecto con editor_user como owner."""
    from app.services.project_service import ProjectService
    from app.schemas.project import ProjectCreate

    service = ProjectService(db_session)
    project = await service.create_project(
        ProjectCreate(name="Proyecto Test", description="Test"),
        editor_user,
    )
    return {"project": project, "owner": editor_user}


# ─────────────────────────────────────────────────────────────────────────────
# Tests de migración — ART-08
# ─────────────────────────────────────────────────────────────────────────────

class TestMigration:
    """Verifica que la migración 0002 creó las tablas correctamente."""

    async def test_projects_table_exists(self, db_session):
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'projects'")
        )
        assert result.scalar_one() == 1, "Tabla 'projects' no existe"

    async def test_project_members_table_exists(self, db_session):
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'project_members'")
        )
        assert result.scalar_one() == 1, "Tabla 'project_members' no existe"

    async def test_project_member_role_enum_exists(self, db_session):
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM pg_type WHERE typname = 'project_member_role'")
        )
        assert result.scalar_one() == 1, "ENUM 'project_member_role' no existe"

    async def test_project_member_role_enum_values(self, db_session):
        result = await db_session.execute(
            text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname = 'project_member_role' ORDER BY enumsortorder")
        )
        values = [row[0] for row in result.fetchall()]
        assert set(values) == {"owner", "editor", "viewer"}

    async def test_projects_deleted_at_is_nullable(self, db_session):
        result = await db_session.execute(
            text("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'projects' AND column_name = 'deleted_at'")
        )
        assert result.scalar_one() == "YES", "deleted_at debe ser nullable (soft delete)"

    async def test_project_members_removed_at_is_nullable(self, db_session):
        result = await db_session.execute(
            text("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'project_members' AND column_name = 'removed_at'")
        )
        assert result.scalar_one() == "YES", "removed_at debe ser nullable (soft delete de membresía)"

    async def test_partial_index_active_members_exists(self, db_session):
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM pg_indexes WHERE indexname = 'ix_project_members_active'")
        )
        assert result.scalar_one() == 1, "Índice parcial ix_project_members_active no existe"


# ─────────────────────────────────────────────────────────────────────────────
# Tests de require_role — ART-01
# ─────────────────────────────────────────────────────────────────────────────

class TestRequireRole:
    """
    ART-01 · R-0201 · R-0202
    Criterio: bloquea con 403 a cualquier rol no listado.
    """

    async def test_admin_can_access_admin_endpoint(
        self, client: AsyncClient, admin_user: User
    ):
        token = generate_test_token(admin_user)
        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_editor_cannot_access_admin_endpoint(
        self, client: AsyncClient, editor_user: User
    ):
        """Editor no puede acceder a endpoint de admin — retorna 403."""
        token = generate_test_token(editor_user)
        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == "FORBIDDEN"
        assert "editor" in body["error"]["message"] or "admin" in body["error"]["message"]

    async def test_viewer_cannot_access_admin_endpoint(
        self, client: AsyncClient, viewer_user: User
    ):
        token = generate_test_token(viewer_user)
        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_missing_token_returns_401(self, client: AsyncClient):
        """Sin token — retorna 401, no 403."""
        response = await client.get("/admin/users")
        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        response = await client.get(
            "/admin/users",
            headers={"Authorization": "Bearer token_invalido_xyz"},
        )
        assert response.status_code == 401

    async def test_error_response_has_correct_format(
        self, client: AsyncClient, viewer_user: User
    ):
        """El formato de error debe seguir el estándar del proyecto."""
        token = generate_test_token(viewer_user)
        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = response.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests de verify_project_membership — ART-02
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyProjectMembership:
    """
    ART-02 · R-0202
    Criterio: 403 sin membresía activa, 404 si proyecto no existe/deleted.
    """

    async def test_owner_can_access_project(
        self, client: AsyncClient, project_with_owner: dict
    ):
        project = project_with_owner["project"]
        owner = project_with_owner["owner"]
        token = generate_test_token(owner)
        response = await client.get(
            f"/projects/{project.id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_non_member_cannot_access_project(
        self, client: AsyncClient, project_with_owner: dict, viewer_user: User
    ):
        """Usuario sin membresía activa recibe 403, no 404."""
        project = project_with_owner["project"]
        token = generate_test_token(viewer_user)
        response = await client.get(
            f"/projects/{project.id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == "FORBIDDEN"

    async def test_removed_member_cannot_access_project(
        self, client: AsyncClient, project_with_owner: dict, db_session, viewer_user: User
    ):
        """Miembro con removed_at IS NOT NULL es tratado como sin membresía."""
        project = project_with_owner["project"]
        owner = project_with_owner["owner"]

        # Agregar y luego remover al viewer
        from app.services.project_service import ProjectService
        service = ProjectService(db_session)
        owner_membership = await service.repo.get_active_membership(project.id, owner.id)

        await service.add_member(
            project.id, viewer_user.id, ProjectMemberRole.viewer,
            owner, owner_membership
        )
        await service.remove_member(project.id, viewer_user.id, owner, owner_membership)

        # Viewer removido intenta acceder
        token = generate_test_token(viewer_user)
        response = await client.get(
            f"/projects/{project.id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_deleted_project_returns_404(
        self, client: AsyncClient, project_with_owner: dict, db_session
    ):
        """Proyecto soft-deleted retorna 404 a cualquier usuario."""
        project = project_with_owner["project"]
        owner = project_with_owner["owner"]

        from app.services.project_service import ProjectService
        service = ProjectService(db_session)
        owner_membership = await service.repo.get_active_membership(project.id, owner.id)
        await service.delete_project(project.id, owner, owner_membership)

        token = generate_test_token(owner)
        response = await client.get(
            f"/projects/{project.id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_access_any_project(
        self, client: AsyncClient, project_with_owner: dict, admin_user: User
    ):
        """Admin del sistema puede acceder a cualquier proyecto sin membresía explícita."""
        project = project_with_owner["project"]
        token = generate_test_token(admin_user)
        response = await client.get(
            f"/projects/{project.id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_nonexistent_project_returns_404(
        self, client: AsyncClient, editor_user: User
    ):
        token = generate_test_token(editor_user)
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/projects/{fake_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Tests de seguridad — escalada de privilegios (riesgo crítico del kick-off)
# ─────────────────────────────────────────────────────────────────────────────

class TestPrivilegeEscalation:
    """
    Riesgo crítico identificado en kick-off: un editor no debe poder
    añadirse a sí mismo como owner (ART-07, test de seguridad explícito).
    """

    async def test_editor_cannot_assign_owner_role(
        self, client: AsyncClient, project_with_owner: dict, editor_user: User, db_session
    ):
        """Editor en el proyecto no puede agregar a otro usuario con rol owner."""
        project = project_with_owner["project"]
        original_owner = project_with_owner["owner"]

        # Agregar editor_user como editor del proyecto
        from app.services.project_service import ProjectService
        service = ProjectService(db_session)
        owner_membership = await service.repo.get_active_membership(project.id, original_owner.id)
        another_editor = await create_test_user(db_session, role="editor", username="editor2_test")

        await service.add_member(
            project.id, another_editor.id, ProjectMemberRole.editor,
            original_owner, owner_membership
        )

        # another_editor intenta agregar a sí mismo como owner
        token = generate_test_token(another_editor)
        response = await client.post(
            f"/projects/{project.id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(another_editor.id), "role": "owner"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == "FORBIDDEN"

    async def test_cannot_remove_owner_directly(
        self, client: AsyncClient, project_with_owner: dict, admin_user: User
    ):
        """El owner no puede ser removido directamente — debe transferir primero."""
        project = project_with_owner["project"]
        owner = project_with_owner["owner"]
        token = generate_test_token(admin_user)
        response = await client.delete(
            f"/projects/{project.id}/members/{owner.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "CANNOT_REMOVE_OWNER"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (se mueven a conftest.py en la implementación real)
# ─────────────────────────────────────────────────────────────────────────────

async def create_test_user(db_session, role: str, username: str) -> User:
    """Helper: crea usuario de prueba. En producción va en conftest.py."""
    from app.services.auth_service import AuthService
    from app.schemas.auth import RegisterRequest

    service = AuthService(db_session)
    user = await service.register(
        RegisterRequest(
            email=f"{username}@test.local",
            username=username,
            password="Test1234!",
            full_name=f"Test {username}",
            timezone="America/Costa_Rica",
        )
    )
    user.role = role
    user.is_verified = True
    await db_session.commit()
    await db_session.refresh(user)
    return user


def generate_test_token(user: User) -> str:
    """Helper: genera JWT de prueba. En producción va en conftest.py."""
    from app.core.security import create_access_token
    return create_access_token({"sub": str(user.id), "role": user.role})