"""
Tests de integración — Sprint 2
ART-07 · R-0201 a R-0205 (E02) · R-0301 a R-0307 (E03)

Patrón idéntico a tests/integration/test_auth.py:
  - asyncio_mode="auto" (pyproject.toml)
  - Fixtures: client, db_session, clean_tables (autouse, conftest.py)
  - Emails mockeados via patch en conftest.py (send_reset_password_email)
  - Un assert por escenario, mensaje descriptivo en caso de fallo

Cobertura objetivo:
  - require_role():              happy path + rol insuficiente + sin token
  - verify_project_membership(): activo + sin membresía + removido + admin bypass
  - CRUD proyectos:              crear + listar + editar + soft-delete
  - Membresía:                   agregar + remover + historial
  - Ownership:                   transferir + validaciones
  - Seguridad:                   escalada de privilegios + último admin
  - forgot/reset password:       flujo completo + token reutilizado + email inexistente
"""

from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMember
from app.models.user import User

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — mismo estilo que test_auth.py
# ─────────────────────────────────────────────────────────────────────────────


async def _register_and_verify(
    client: AsyncClient, email: str, username: str, password: str = "Test1234!"
) -> dict:
    """Registra y verifica un usuario, retorna {id, email, username, password}."""
    captured: dict = {}

    async def fake_send(email_, username_, code):
        captured["code"] = code

    with patch(
        "app.services.auth_service.send_verification_email", side_effect=fake_send
    ):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
                "full_name": f"Test {username}",
                "timezone": "UTC",
            },
        )
    assert resp.status_code == 201, f"register falló: {resp.text}"

    resp2 = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": email,
            "code": captured["code"],
        },
    )
    assert resp2.status_code == 200, f"verify falló: {resp2.text}"

    return {
        "id": resp.json()["user_id"],
        "email": email,
        "username": username,
        "password": password,
    }


async def _login(client: AsyncClient, email: str, password: str = "Test1234!") -> str:
    """Retorna el access_token."""
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, f"login falló: {resp.text}"
    return resp.json()["access_token"]


async def _headers(
    client: AsyncClient, email: str, password: str = "Test1234!"
) -> dict:
    token = await _login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


async def _set_role(db: AsyncSession, user_id: str, role: str) -> None:
    """Helper: cambia el rol de un usuario directamente en DB (para setup de tests)."""
    await db.execute(update(User).where(User.id == UUID(user_id)).values(role=role))
    await db.commit()


async def _create_project(
    client: AsyncClient, headers: dict, name: str = "Proyecto Test"
) -> dict:
    """Crea un proyecto y retorna el JSON del response."""
    resp = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"create_project falló: {resp.text}"
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# E02 — require_role: acceso por rol global  (ART-01 · R-0201)
# ─────────────────────────────────────────────────────────────────────────────


class TestRequireRole:
    """ART-01 · R-0201 · R-0202 — middleware RBAC global"""

    async def test_admin_accede_a_lista_usuarios(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await _register_and_verify(client, "admin@test.dev", "adminuser")
        await _set_role(db_session, user["id"], "admin")
        headers = await _headers(client, user["email"])

        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 200, "Admin debe poder listar usuarios"

    async def test_editor_no_puede_listar_usuarios(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Editor recibe 403 en endpoint de admin — no 401."""
        user = await _register_and_verify(client, "editor@test.dev", "editoruser")
        # El segundo usuario registrado recibe rol editor (AG-01)
        headers = await _headers(client, user["email"])

        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403, "Editor no debe acceder a admin/users"
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    async def test_viewer_no_puede_listar_usuarios(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await _register_and_verify(client, "viewer@test.dev", "vieweruser")
        await _set_role(db_session, user["id"], "viewer")
        headers = await _headers(client, user["email"])

        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403, "Viewer no debe acceder a admin/users"

    async def test_sin_token_retorna_401_no_403(self, client: AsyncClient):
        """Sin token → 401. Con token de rol insuficiente → 403."""
        resp = await client.get("/api/v1/admin/users")
        assert resp.status_code == 401, "Sin token debe retornar 401, no 403"

    async def test_token_invalido_retorna_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": "Bearer token.invalido.aqui"},
        )
        assert resp.status_code == 401, "Token inválido debe retornar 401"

    async def test_error_sigue_formato_estandar(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """El response de error de RBAC debe seguir {error: {code, message}}."""
        user = await _register_and_verify(client, "fmt@test.dev", "fmtuser")
        await _set_role(db_session, user["id"], "viewer")
        headers = await _headers(client, user["email"])

        resp = await client.get("/api/v1/admin/users", headers=headers)
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]


# ─────────────────────────────────────────────────────────────────────────────
# E02 — Admin: cambio de rol (ART-04 · R-0204)
# ─────────────────────────────────────────────────────────────────────────────


class TestChangeRole:
    """ART-04 · R-0204 — PATCH /admin/users/{id}/role"""

    async def test_admin_cambia_rol_de_editor_a_viewer(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await _register_and_verify(client, "a1@test.dev", "admin1")
        await _set_role(db_session, admin["id"], "admin")
        target = await _register_and_verify(client, "t1@test.dev", "target1")
        headers = await _headers(client, admin["email"])

        resp = await client.patch(
            f"/api/v1/admin/users/{target['id']}/role",
            json={"role": "viewer"},
            headers=headers,
        )
        assert resp.status_code == 200, f"cambio de rol falló: {resp.text}"
        assert resp.json()["role"] == "viewer"

    async def test_no_se_puede_degradar_ultimo_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Si solo hay un admin, degradarlo debe retornar 422 CANNOT_REMOVE_LAST_ADMIN."""
        admin = await _register_and_verify(client, "a2@test.dev", "admin2")
        await _set_role(db_session, admin["id"], "admin")
        headers = await _headers(client, admin["email"])

        resp = await client.patch(
            f"/api/v1/admin/users/{admin['id']}/role",
            json={"role": "editor"},
            headers=headers,
        )
        assert resp.status_code == 422, "Degradar al único admin debe retornar 422"
        assert resp.json()["error"]["code"] == "CANNOT_REMOVE_LAST_ADMIN"

    async def test_rol_invalido_retorna_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await _register_and_verify(client, "a3@test.dev", "admin3")
        await _set_role(db_session, admin["id"], "admin")
        target = await _register_and_verify(client, "t3@test.dev", "target3")
        headers = await _headers(client, admin["email"])

        resp = await client.patch(
            f"/api/v1/admin/users/{target['id']}/role",
            json={"role": "superadmin"},
            headers=headers,
        )
        assert resp.status_code == 422, "Rol inválido debe retornar 422"

    async def test_cambio_idempotente(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cambiar al mismo rol que ya tiene no debe fallar."""
        admin = await _register_and_verify(client, "a4@test.dev", "admin4")
        await _set_role(db_session, admin["id"], "admin")
        target = await _register_and_verify(client, "t4@test.dev", "target4")
        headers = await _headers(client, admin["email"])

        # El target ya es editor — cambiar a editor de nuevo
        resp = await client.patch(
            f"/api/v1/admin/users/{target['id']}/role",
            json={"role": "editor"},
            headers=headers,
        )
        assert resp.status_code == 200, "Cambio idempotente debe retornar 200"


# ─────────────────────────────────────────────────────────────────────────────
# E03 — verify_project_membership (ART-02 · R-0202)
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectMembership:
    """ART-02 · R-0202 — verify_project_membership dependency"""

    async def test_owner_accede_al_proyecto(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "own@test.dev", "owner1")
        headers = await _headers(client, owner["email"])
        project = await _create_project(client, headers)

        resp = await client.get(
            f"/api/v1/projects/{project['id']}/members", headers=headers
        )
        assert resp.status_code == 200, "Owner debe poder ver los miembros"

    async def test_no_miembro_recibe_403_no_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Usuario sin membresía activa recibe 403 — no 404 para no revelar existencia."""
        owner = await _register_and_verify(client, "own2@test.dev", "owner2")
        stranger = await _register_and_verify(client, "str@test.dev", "stranger1")

        owner_h = await _headers(client, owner["email"])
        stranger_h = await _headers(client, stranger["email"])

        project = await _create_project(client, owner_h)

        resp = await client.get(
            f"/api/v1/projects/{project['id']}/members",
            headers=stranger_h,
        )
        assert resp.status_code == 403, "No-miembro debe recibir 403, no 404"

    async def test_miembro_removido_recibe_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Miembro con removed_at IS NOT NULL es tratado como sin membresía."""
        owner = await _register_and_verify(client, "own3@test.dev", "owner3")
        member = await _register_and_verify(client, "mem3@test.dev", "member3")

        owner_h = await _headers(client, owner["email"])
        member_h = await _headers(client, member["email"])

        project = await _create_project(client, owner_h)

        # Agregar y luego remover al miembro
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member["id"], "role": "viewer"},
            headers=owner_h,
        )
        await client.delete(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=owner_h,
        )

        # Miembro removido intenta acceder
        resp = await client.get(
            f"/api/v1/projects/{project['id']}/members",
            headers=member_h,
        )
        assert resp.status_code == 403, "Miembro removido debe recibir 403"

    async def test_admin_accede_sin_ser_miembro(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin del sistema accede a cualquier proyecto sin membresía explícita."""
        owner = await _register_and_verify(client, "own4@test.dev", "owner4")
        admin = await _register_and_verify(client, "adm4@test.dev", "admin4sys")
        await _set_role(db_session, admin["id"], "admin")

        owner_h = await _headers(client, owner["email"])
        admin_h = await _headers(client, admin["email"])

        project = await _create_project(client, owner_h)

        resp = await client.get(
            f"/api/v1/projects/{project['id']}/members",
            headers=admin_h,
        )
        assert resp.status_code == 200, "Admin debe acceder sin membresía explícita"

    async def test_proyecto_inexistente_retorna_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await _register_and_verify(client, "u404@test.dev", "user404")
        headers = await _headers(client, user["email"])

        resp = await client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/members",
            headers=headers,
        )
        assert resp.status_code == 404, "Proyecto inexistente debe retornar 404"


# ─────────────────────────────────────────────────────────────────────────────
# E03 — CRUD proyectos (ART-09 · R-0301 · R-0302)
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectCRUD:
    """ART-09 · R-0301 · R-0302 — CRUD completo de proyectos"""

    async def test_crear_proyecto_registra_owner_como_miembro(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await _register_and_verify(client, "cr1@test.dev", "creator1")
        headers = await _headers(client, user["email"])
        project = await _create_project(client, headers, "Mi Proyecto")

        # Verificar que el creador aparece como miembro owner
        members = await client.get(
            f"/api/v1/projects/{project['id']}/members",
            headers=headers,
        )
        assert members.status_code == 200
        roles = [m["role"] for m in members.json()]
        assert "owner" in roles, "El creador debe quedar como owner en project_members"

    async def test_viewer_no_puede_crear_proyecto(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await _register_and_verify(client, "vw1@test.dev", "viewer1cr")
        await _set_role(db_session, user["id"], "viewer")
        headers = await _headers(client, user["email"])

        resp = await client.post(
            "/api/v1/projects", json={"name": "No permitido"}, headers=headers
        )
        assert resp.status_code == 403, "Viewer no puede crear proyectos"

    async def test_listar_solo_proyectos_del_usuario(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        u1 = await _register_and_verify(client, "lst1@test.dev", "lister1")
        u2 = await _register_and_verify(client, "lst2@test.dev", "lister2")

        h1 = await _headers(client, u1["email"])
        h2 = await _headers(client, u2["email"])

        await _create_project(client, h1, "Proyecto de U1")
        await _create_project(client, h2, "Proyecto de U2")

        resp = await client.get("/api/v1/projects", headers=h1)
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()["items"]]
        assert "Proyecto de U1" in names
        assert "Proyecto de U2" not in names, "U1 no debe ver proyectos de U2"

    async def test_editar_proyecto_solo_owner(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "ed1@test.dev", "editor_own1")
        member = await _register_and_verify(client, "ed2@test.dev", "editor_mem1")

        owner_h = await _headers(client, owner["email"])
        member_h = await _headers(client, member["email"])

        project = await _create_project(client, owner_h)

        # Agregar member como viewer
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member["id"], "role": "viewer"},
            headers=owner_h,
        )

        # Viewer intenta editar
        resp = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Nombre cambiado por viewer"},
            headers=member_h,
        )
        assert resp.status_code == 403, "Viewer no puede editar el proyecto"

        # Owner edita correctamente
        resp2 = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Nombre actualizado"},
            headers=owner_h,
        )
        assert resp2.status_code == 200
        assert resp2.json()["name"] == "Nombre actualizado"

    async def test_soft_delete_proyecto_sin_tareas(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Proyecto sin tareas activas puede eliminarse — soft delete correcto."""
        owner = await _register_and_verify(client, "del1@test.dev", "delowner1")
        headers = await _headers(client, owner["email"])
        project = await _create_project(client, headers)

        resp = await client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
        assert resp.status_code == 204, "Soft delete debe retornar 204"

        # No debe aparecer en el listado
        lista = await client.get("/api/v1/projects", headers=headers)
        ids = [p["id"] for p in lista.json()["items"]]
        assert (
            project["id"] not in ids
        ), "Proyecto eliminado no debe aparecer en listado"

    async def test_soft_delete_retorna_409_con_tareas_activas(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Con Task model de S3 aún no existente, este test se skippea
        automáticamente. Se habilitará en Sprint 3.
        R-0302 — decisión cerrada en kick-off: rechazar, no archivar.
        """
        pytest.skip("Task model disponible en Sprint 3 — reactivar en S3")


# ─────────────────────────────────────────────────────────────────────────────
# E03 — Gestión de miembros (ART-10 · R-0303)
# ─────────────────────────────────────────────────────────────────────────────


class TestMembership:
    """ART-10 · R-0303 — agregar, remover, historial"""

    async def test_agregar_miembro_como_viewer(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "mo1@test.dev", "memown1")
        new_member = await _register_and_verify(client, "mm1@test.dev", "newmem1")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        resp = await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": new_member["id"], "role": "viewer"},
            headers=owner_h,
        )
        assert resp.status_code == 201, f"agregar miembro falló: {resp.text}"
        assert resp.json()["role"] == "viewer"

    async def test_no_se_puede_agregar_miembro_duplicado(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "mo2@test.dev", "memown2")
        member = await _register_and_verify(client, "mm2@test.dev", "newmem2")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member["id"], "role": "viewer"},
            headers=owner_h,
        )
        resp2 = await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member["id"], "role": "editor"},
            headers=owner_h,
        )
        assert resp2.status_code == 409, "Miembro duplicado debe retornar 409"
        assert resp2.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"

    async def test_remover_miembro_es_soft_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Al remover, el registro persiste en la DB con removed_at IS NOT NULL."""
        owner = await _register_and_verify(client, "mo3@test.dev", "memown3")
        member = await _register_and_verify(client, "mm3@test.dev", "newmem3")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member["id"], "role": "viewer"},
            headers=owner_h,
        )

        resp = await client.delete(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=owner_h,
        )
        assert resp.status_code == 204, "Remover miembro debe retornar 204"

        # Verificar que el registro persiste en DB con removed_at
        result = await db_session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == UUID(project["id"]),
                ProjectMember.user_id == UUID(member["id"]),
            )
        )
        pm = result.scalar_one_or_none()
        assert pm is not None, "El registro de membresía debe persistir (soft delete)"
        assert pm.removed_at is not None, "removed_at debe estar establecido"

    async def test_no_se_puede_remover_al_owner(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "mo4@test.dev", "memown4")
        admin = await _register_and_verify(client, "adm5@test.dev", "admin5sys")
        await _set_role(db_session, admin["id"], "admin")

        owner_h = await _headers(client, owner["email"])
        admin_h = await _headers(client, admin["email"])
        project = await _create_project(client, owner_h)

        resp = await client.delete(
            f"/api/v1/projects/{project['id']}/members/{owner['id']}",
            headers=admin_h,
        )
        assert resp.status_code == 409, "No se puede remover al owner directamente"
        assert resp.json()["error"]["code"] == "CANNOT_REMOVE_OWNER"

    async def test_historial_incluye_miembros_removidos(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "mo5@test.dev", "memown5")
        member = await _register_and_verify(client, "mm5@test.dev", "newmem5")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": member["id"], "role": "viewer"},
            headers=owner_h,
        )
        await client.delete(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=owner_h,
        )

        resp = await client.get(
            f"/api/v1/projects/{project['id']}/members/history",
            headers=owner_h,
        )
        assert resp.status_code == 200
        all_ids = [m["user_id"] for m in resp.json()["items"]]
        assert member["id"] in all_ids, "El historial debe incluir al miembro removido"


# ─────────────────────────────────────────────────────────────────────────────
# E03 — Transferencia de ownership (ART-11 · R-0304 · DU-02)
# ─────────────────────────────────────────────────────────────────────────────


class TestOwnershipTransfer:
    """ART-11 · R-0304 · DU-02 — transferencia atómica de ownership"""

    async def test_transferir_ownership_exitoso(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "ot1@test.dev", "owntr1")
        new_owner = await _register_and_verify(client, "no1@test.dev", "newown1")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        # Agregar al nuevo owner como miembro
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": new_owner["id"], "role": "editor"},
            headers=owner_h,
        )

        resp = await client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json={"new_owner_id": new_owner["id"]},
            headers=owner_h,
        )
        assert resp.status_code == 200, f"transferencia falló: {resp.text}"

        # Verificar cambios en DB — nuevo owner tiene rol owner
        result = await db_session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == UUID(project["id"]),
                ProjectMember.user_id == UUID(new_owner["id"]),
                ProjectMember.removed_at.is_(None),
            )
        )
        pm = result.scalar_one_or_none()
        assert pm is not None and pm.role == "owner", "Nuevo owner debe tener rol owner"

    async def test_owner_anterior_queda_como_editor(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """La transferencia es atómica: el owner anterior queda como editor."""
        owner = await _register_and_verify(client, "ot2@test.dev", "owntr2")
        new_owner = await _register_and_verify(client, "no2@test.dev", "newown2")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": new_owner["id"], "role": "editor"},
            headers=owner_h,
        )
        await client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json={"new_owner_id": new_owner["id"]},
            headers=owner_h,
        )

        result = await db_session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == UUID(project["id"]),
                ProjectMember.user_id == UUID(owner["id"]),
                ProjectMember.removed_at.is_(None),
            )
        )
        pm = result.scalar_one_or_none()
        assert (
            pm is not None and pm.role == "editor"
        ), "Owner anterior debe quedar como editor"

    async def test_no_miembro_no_puede_recibir_ownership(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "ot3@test.dev", "owntr3")
        stranger = await _register_and_verify(client, "st3@test.dev", "stranger3")

        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        resp = await client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json={"new_owner_id": stranger["id"]},
            headers=owner_h,
        )
        assert resp.status_code == 404, "No-miembro no puede recibir ownership"

    async def test_no_se_puede_transferir_a_si_mismo(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "ot4@test.dev", "owntr4")
        owner_h = await _headers(client, owner["email"])
        project = await _create_project(client, owner_h)

        resp = await client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json={"new_owner_id": owner["id"]},
            headers=owner_h,
        )
        assert resp.status_code == 409, "No se puede transferir ownership a uno mismo"

    async def test_solo_owner_puede_transferir(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "ot5@test.dev", "owntr5")
        editor = await _register_and_verify(client, "ed5@test.dev", "editortr5")

        owner_h = await _headers(client, owner["email"])
        editor_h = await _headers(client, editor["email"])
        project = await _create_project(client, owner_h)

        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": editor["id"], "role": "editor"},
            headers=owner_h,
        )

        # Editor intenta transferir
        resp = await client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json={"new_owner_id": owner["id"]},
            headers=editor_h,
        )
        assert resp.status_code == 403, "Editor no puede transferir ownership"


# ─────────────────────────────────────────────────────────────────────────────
# Seguridad — escalada de privilegios (riesgo crítico del kick-off)
# ─────────────────────────────────────────────────────────────────────────────


class TestPrivilegeEscalation:
    """
    Riesgo crítico identificado en kick-off.
    Un editor no debe poder asignarse a sí mismo como owner.
    """

    async def test_editor_no_puede_asignar_rol_owner(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "pe1@test.dev", "privesc1")
        editor = await _register_and_verify(client, "pe2@test.dev", "privesc2")
        victim = await _register_and_verify(client, "pe3@test.dev", "privesc3")

        owner_h = await _headers(client, owner["email"])
        editor_h = await _headers(client, editor["email"])
        project = await _create_project(client, owner_h)

        # Agregar editor como editor del proyecto
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": editor["id"], "role": "editor"},
            headers=owner_h,
        )

        # Editor intenta agregar a victim como owner
        resp = await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": victim["id"], "role": "owner"},
            headers=editor_h,
        )
        assert (
            resp.status_code == 403
        ), "Editor no puede asignar rol owner — escalada de privilegios"
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    async def test_viewer_no_puede_agregar_miembros(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await _register_and_verify(client, "pe4@test.dev", "privesc4")
        viewer = await _register_and_verify(client, "pe5@test.dev", "privesc5")
        victim = await _register_and_verify(client, "pe6@test.dev", "privesc6")

        owner_h = await _headers(client, owner["email"])
        viewer_h = await _headers(client, viewer["email"])
        project = await _create_project(client, owner_h)

        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": viewer["id"], "role": "viewer"},
            headers=owner_h,
        )

        resp = await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": victim["id"], "role": "viewer"},
            headers=viewer_h,
        )
        assert resp.status_code == 403, "Viewer no puede agregar miembros"


# ─────────────────────────────────────────────────────────────────────────────
# E02 — forgot/reset password (ART-05 · R-0205)
# ─────────────────────────────────────────────────────────────────────────────


class TestForgotResetPassword:
    """
    ART-05 · R-0205 — flujo completo de recuperación de contraseña.
    send_reset_password_email está mockeado en conftest.py.
    El token se captura interceptando el mock para simular el flujo completo.
    """

    async def test_forgot_password_siempre_retorna_200(self, client: AsyncClient):
        """No revela si el email existe — siempre 200."""
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "noexiste@test.dev"},
        )
        assert resp.status_code == 200, "forgot-password siempre debe retornar 200"

    async def test_forgot_password_email_existente_retorna_200(
        self, client: AsyncClient
    ):
        user = await _register_and_verify(client, "fp1@test.dev", "fpuser1")

        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user["email"]},
        )
        assert resp.status_code == 200

    async def test_flujo_completo_reset_password(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Flujo end-to-end: forgot → capturar token → reset → login con nueva contraseña."""
        user = await _register_and_verify(client, "fp2@test.dev", "fpuser2")

        # Capturar el token que se pasaría al email
        captured_token: dict = {}

        async def capture_reset(email, username, reset_url):
            # El reset_url tiene el formato: .../reset-password?token=XXXXX
            token = reset_url.split("token=")[-1]
            captured_token["token"] = token

        with patch(
            "app.services.auth_service.send_reset_password_email",
            side_effect=capture_reset,
        ):
            await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user["email"]},
            )

        assert "token" in captured_token, "El token debe haberse capturado del email"

        # Resetear contraseña con el token capturado
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": captured_token["token"], "new_password": "NuevaClave1!"},
        )
        assert resp.status_code == 200, f"reset-password falló: {resp.text}"

        # Login con la nueva contraseña debe funcionar
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": "NuevaClave1!"},
        )
        assert (
            login_resp.status_code == 200
        ), "Login con nueva contraseña debe funcionar"

        # Login con la contraseña antigua debe fallar
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": "Test1234!"},
        )
        assert old_login.status_code == 401, "Login con contraseña antigua debe fallar"

    async def test_token_de_reset_es_de_un_solo_uso(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Segundo uso del mismo token → error (TOKEN_INVALID)."""
        user = await _register_and_verify(client, "fp3@test.dev", "fpuser3")

        captured_token: dict = {}

        async def capture_reset(email, username, reset_url):
            captured_token["token"] = reset_url.split("token=")[-1]

        with patch(
            "app.services.auth_service.send_reset_password_email",
            side_effect=capture_reset,
        ):
            await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user["email"]},
            )

        # Primer uso — exitoso
        await client.post(
            "/api/v1/auth/reset-password",
            json={"token": captured_token["token"], "new_password": "NuevaClave1!"},
        )

        # Segundo uso — debe fallar
        resp2 = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": captured_token["token"], "new_password": "OtraClave2!"},
        )
        assert resp2.status_code in (400, 401), "Segundo uso del token debe fallar"

    async def test_reset_revoca_refresh_tokens_activos(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Al resetear, todos los refresh tokens del usuario quedan revocados."""
        user = await _register_and_verify(client, "fp4@test.dev", "fpuser4")

        # Login para obtener refresh token
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": "Test1234!"},
        )
        assert login.status_code == 200

        captured_token: dict = {}

        async def capture_reset(email, username, reset_url):
            captured_token["token"] = reset_url.split("token=")[-1]

        with patch(
            "app.services.auth_service.send_reset_password_email",
            side_effect=capture_reset,
        ):
            await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user["email"]},
            )

        await client.post(
            "/api/v1/auth/reset-password",
            json={"token": captured_token["token"], "new_password": "NuevaClave1!"},
        )

        # Intentar usar el refresh token anterior debe fallar
        refresh_resp = await client.post("/api/v1/auth/refresh")
        assert refresh_resp.status_code in (
            401,
            403,
        ), "Refresh token anterior debe estar revocado después del reset"
