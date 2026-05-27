"""
Tests de integración — Sprint 2
ART-07 · R-0201 a R-0205 (E02) · R-0301 a R-0307 (E03)

Patrón idéntico a tests/integration/test_auth.py del repo:
  - Funciones planas (no clases) con @pytest.mark.asyncio
  - asyncio_mode="auto" en pyproject.toml
  - Fixtures: client, db_session, clean_tables (autouse conftest.py)
  - send_verification_email y send_reset_password_email mockeados en conftest.py
  - El código de verificación se captura con side_effect local (mismo patrón test_auth.py)
  - Timezone: UTC (siempre disponible sin tzdata)
"""

from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember
from app.models.user import User


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — mismo estilo que test_auth.py
# ─────────────────────────────────────────────────────────────────────────────

async def _register(client: AsyncClient, email: str, username: str, password: str = "Test1234!") -> str:
    """Registra un usuario y retorna el código de verificación capturado."""
    captured = {}

    async def fake_send(e, u, code):
        captured["code"] = code

    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
        resp = await client.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": f"Test {username}",
            "timezone": "UTC",
        })
    assert resp.status_code == 201, f"register falló ({resp.status_code}): {resp.text}"
    return captured["code"]


async def _verify(client: AsyncClient, email: str, code: str) -> None:
    resp = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    assert resp.status_code == 200, f"verify falló ({resp.status_code}): {resp.text}"


async def _register_and_verify(client: AsyncClient, email: str, username: str, password: str = "Test1234!") -> dict:
    """Registra y verifica. Retorna {email, username, password}."""
    code = await _register(client, email, username, password)
    await _verify(client, email, code)
    return {"email": email, "username": username, "password": password}


async def _login(client: AsyncClient, email: str, password: str = "Test1234!") -> str:
    """Retorna access_token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"login falló ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


async def _headers(client: AsyncClient, email: str, password: str = "Test1234!") -> dict:
    token = await _login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


async def _set_role(db: AsyncSession, email: str, role: str) -> None:
    """Cambia el rol de un usuario directamente en DB — solo para setup de tests."""
    await db.execute(update(User).where(User.email == email).values(role=role))
    await db.commit()


async def _create_project(client: AsyncClient, headers: dict, name: str = "Proyecto Test") -> dict:
    resp = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"create_project falló ({resp.status_code}): {resp.text}"
    return resp.json()


async def _get_reset_token(client: AsyncClient, email: str) -> str:
    """Dispara forgot-password y captura el token del reset_url."""
    captured = {}

    async def capture(e, u, reset_url):
        captured["token"] = reset_url.split("token=")[-1]

    with patch("app.services.auth_service.send_reset_password_email", side_effect=capture):
        resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    return captured["token"]


# ─────────────────────────────────────────────────────────────────────────────
# E02 — require_role (ART-01 · R-0201)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_accede_a_lista_usuarios(client, db_session):
    """Admin puede listar usuarios."""
    user = await _register_and_verify(client, "admin1@test.dev", "admin1")
    await _set_role(db_session, user["email"], "admin")
    headers = await _headers(client, user["email"])

    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200, f"Admin debe ver usuarios: {resp.text}"


@pytest.mark.asyncio
async def test_editor_no_puede_listar_usuarios(client):
    await _register_and_verify(client, "admin_ag01@test.dev", "admin_ag01")  # ← AÑADIR
    editor = await _register_and_verify(client, "editor1@test.dev", "editor1")
    headers = await _headers(client, editor["email"])

    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403, "Editor no puede acceder a admin/users"
    assert resp.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_viewer_no_puede_listar_usuarios(client, db_session):
    """Viewer recibe 403."""
    user = await _register_and_verify(client, "viewer1@test.dev", "viewer1")
    await _set_role(db_session, user["email"], "viewer")
    headers = await _headers(client, user["email"])

    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403, "Viewer no puede acceder a admin/users"


@pytest.mark.asyncio
async def test_sin_token_retorna_401(client):
    """Sin token → 401, no 403."""
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401, "Sin token debe retornar 401"


@pytest.mark.asyncio
async def test_token_invalido_retorna_401(client):
    resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": "Bearer token.invalido.xyz"},
    )
    assert resp.status_code == 401, "Token inválido debe retornar 401"


@pytest.mark.asyncio
async def test_error_rbac_sigue_formato_estandar(client, db_session):
    """El error de RBAC debe seguir {error: {code, message}}."""
    user = await _register_and_verify(client, "fmt1@test.dev", "fmtuser1")
    await _set_role(db_session, user["email"], "viewer")
    headers = await _headers(client, user["email"])

    resp = await client.get("/api/v1/admin/users", headers=headers)
    body = resp.json()
    assert "error" in body and "code" in body["error"] and "message" in body["error"]


# ─────────────────────────────────────────────────────────────────────────────
# E02 — cambio de rol (ART-04 · R-0204)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_cambia_rol_a_viewer(client, db_session):
    admin = await _register_and_verify(client, "adm2@test.dev", "adminrol1")
    await _set_role(db_session, admin["email"], "admin")
    target = await _register_and_verify(client, "tgt2@test.dev", "targetrol1")
    headers = await _headers(client, admin["email"])

    # Obtener el ID del target
    resp_list = await client.get("/api/v1/admin/users", headers=headers)
    target_id = next(u["id"] for u in resp_list.json()["items"] if u["email"] == target["email"])

    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"role": "viewer"},
        headers=headers,
    )
    assert resp.status_code == 200, f"cambio de rol falló: {resp.text}"
    assert resp.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_no_se_puede_degradar_unico_admin(client, db_session):
    """422 CANNOT_REMOVE_LAST_ADMIN si solo queda un admin."""
    admin = await _register_and_verify(client, "adm3@test.dev", "adminrol2")
    await _set_role(db_session, admin["email"], "admin")
    headers = await _headers(client, admin["email"])

    resp_list = await client.get("/api/v1/admin/users", headers=headers)
    admin_id = next(u["id"] for u in resp_list.json()["items"] if u["email"] == admin["email"])

    resp = await client.patch(
        f"/api/v1/admin/users/{admin_id}/role",
        json={"role": "editor"},
        headers=headers,
    )
    assert resp.status_code == 422, "Degradar único admin debe retornar 422"
    assert resp.json()["error"]["code"] == "CANNOT_REMOVE_LAST_ADMIN"


@pytest.mark.asyncio
async def test_rol_invalido_retorna_error_validacion(client, db_session):
    admin = await _register_and_verify(client, "adm4@test.dev", "adminrol3")
    await _set_role(db_session, admin["email"], "admin")
    target = await _register_and_verify(client, "tgt4@test.dev", "targetrol2")
    headers = await _headers(client, admin["email"])

    resp_list = await client.get("/api/v1/admin/users", headers=headers)
    target_id = next(u["id"] for u in resp_list.json()["items"] if u["email"] == target["email"])

    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"role": "superadmin"},
        headers=headers,
    )
    assert resp.status_code == 422, "Rol inválido debe retornar 422"


# ─────────────────────────────────────────────────────────────────────────────
# E03 — verify_project_membership (ART-02 · R-0202)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_owner_accede_al_proyecto(client):
    owner = await _register_and_verify(client, "own1@test.dev", "owner1")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)

    resp = await client.get(f"/api/v1/projects/{project['id']}/members", headers=headers)
    assert resp.status_code == 200, "Owner debe ver los miembros"


@pytest.mark.asyncio
async def test_no_miembro_recibe_403_no_404(client):
    """403 — no 404 — para no revelar existencia del proyecto."""
    owner = await _register_and_verify(client, "own2@test.dev", "owner2")
    stranger = await _register_and_verify(client, "str1@test.dev", "stranger1")

    owner_h = await _headers(client, owner["email"])
    stranger_h = await _headers(client, stranger["email"])
    project = await _create_project(client, owner_h)

    resp = await client.get(f"/api/v1/projects/{project['id']}/members", headers=stranger_h)
    assert resp.status_code == 403, "No-miembro debe recibir 403"


@pytest.mark.asyncio
async def test_miembro_removido_recibe_403(client):
    owner = await _register_and_verify(client, "own3@test.dev", "owner3")
    member = await _register_and_verify(client, "mem1@test.dev", "member1")

    owner_h = await _headers(client, owner["email"])
    member_h = await _headers(client, member["email"])
    project = await _create_project(client, owner_h)

    # Agregar y luego remover
    resp_m = await client.get("/api/v1/admin/users", headers=owner_h)
    # Obtener member_id via listado de miembros tras agregarlo
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": (await client.get("/api/v1/users/me", headers=member_h)).json()["id"], "role": "viewer"},
        headers=owner_h,
    )
    member_id = (await client.get("/api/v1/users/me", headers=member_h)).json()["id"]
    await client.delete(f"/api/v1/projects/{project['id']}/members/{member_id}", headers=owner_h)

    resp = await client.get(f"/api/v1/projects/{project['id']}/members", headers=member_h)
    assert resp.status_code == 403, "Miembro removido debe recibir 403"


@pytest.mark.asyncio
async def test_admin_sistema_accede_sin_ser_miembro(client, db_session):
    """Admin del sistema accede a cualquier proyecto aunque no sea miembro."""
    owner = await _register_and_verify(client, "own4@test.dev", "owner4")
    admin = await _register_and_verify(client, "sys1@test.dev", "sysadmin1")
    await _set_role(db_session, admin["email"], "admin")

    owner_h = await _headers(client, owner["email"])
    admin_h = await _headers(client, admin["email"])
    project = await _create_project(client, owner_h)

    resp = await client.get(f"/api/v1/projects/{project['id']}/members", headers=admin_h)
    assert resp.status_code == 200, "Admin accede sin membresía explícita"


@pytest.mark.asyncio
async def test_proyecto_inexistente_retorna_404(client):
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

@pytest.mark.asyncio
async def test_crear_proyecto_registra_creador_como_owner(client):
    user = await _register_and_verify(client, "cr1@test.dev", "creator1")
    headers = await _headers(client, user["email"])
    project = await _create_project(client, headers, "Mi Proyecto")

    members = await client.get(f"/api/v1/projects/{project['id']}/members", headers=headers)
    assert members.status_code == 200
    roles = [m["role"] for m in members.json()]
    assert "owner" in roles, "Creador debe quedar como owner"


@pytest.mark.asyncio
async def test_viewer_no_puede_crear_proyecto(client, db_session):
    user = await _register_and_verify(client, "vw1@test.dev", "viewer1cr")
    await _set_role(db_session, user["email"], "viewer")
    headers = await _headers(client, user["email"])

    resp = await client.post("/api/v1/projects", json={"name": "No permitido"}, headers=headers)
    assert resp.status_code == 403, "Viewer no puede crear proyectos"


@pytest.mark.asyncio
async def test_listar_solo_proyectos_propios(client):
    u1 = await _register_and_verify(client, "ls1@test.dev", "lister1")
    u2 = await _register_and_verify(client, "ls2@test.dev", "lister2")

    h1 = await _headers(client, u1["email"])
    h2 = await _headers(client, u2["email"])

    await _create_project(client, h1, "Proyecto de U1")
    await _create_project(client, h2, "Proyecto de U2")

    resp = await client.get("/api/v1/projects", headers=h1)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["items"]]
    assert "Proyecto de U1" in names
    assert "Proyecto de U2" not in names, "U1 no debe ver proyectos de U2"


@pytest.mark.asyncio
async def test_solo_owner_puede_editar_proyecto(client):
    owner = await _register_and_verify(client, "ed1@test.dev", "edowner1")
    member = await _register_and_verify(client, "ed2@test.dev", "edmem1")

    owner_h = await _headers(client, owner["email"])
    member_h = await _headers(client, member["email"])
    project = await _create_project(client, owner_h)

    member_id = (await client.get("/api/v1/users/me", headers=member_h)).json()["id"]
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "viewer"},
        headers=owner_h,
    )

    # Viewer intenta editar
    resp = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Editado por viewer"},
        headers=member_h,
    )
    assert resp.status_code == 403, "Viewer no puede editar proyecto"

    # Owner edita correctamente
    resp2 = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Nombre correcto"},
        headers=owner_h,
    )
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Nombre correcto"


@pytest.mark.asyncio
async def test_soft_delete_proyecto_sin_tareas(client, db_session):
    owner = await _register_and_verify(client, "del1@test.dev", "delowner1")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)

    resp = await client.delete(f"/api/v1/projects/{project['id']}", headers=headers)
    assert resp.status_code == 204, "Soft delete debe retornar 204"

    # No debe aparecer en el listado
    lista = await client.get("/api/v1/projects", headers=headers)
    ids = [p["id"] for p in lista.json()["items"]]
    assert project["id"] not in ids, "Proyecto eliminado no debe aparecer en listado"

    # Verificar que el registro persiste con deleted_at en DB
    result = await db_session.execute(
        select(Project).where(Project.id == UUID(project["id"]))
    )
    p = result.scalar_one_or_none()
    assert p is not None and p.deleted_at is not None, "deleted_at debe estar establecido"


@pytest.mark.asyncio
async def test_soft_delete_con_tareas_activas_retorna_409():
    """Task model disponible en Sprint 3 — se activa automáticamente en S3."""
    pytest.skip("Task model disponible en Sprint 3")


# ─────────────────────────────────────────────────────────────────────────────
# E03 — Gestión de miembros (ART-10 · R-0303)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agregar_miembro_como_viewer(client):
    owner = await _register_and_verify(client, "mo1@test.dev", "memown1")
    new_member = await _register_and_verify(client, "mm1@test.dev", "newmem1")

    owner_h = await _headers(client, owner["email"])
    member_h = await _headers(client, new_member["email"])
    project = await _create_project(client, owner_h)
    member_id = (await client.get("/api/v1/users/me", headers=member_h)).json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "viewer"},
        headers=owner_h,
    )
    assert resp.status_code == 201, f"agregar miembro falló: {resp.text}"
    assert resp.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_no_se_puede_agregar_miembro_duplicado(client):
    owner = await _register_and_verify(client, "mo2@test.dev", "memown2")
    member = await _register_and_verify(client, "mm2@test.dev", "newmem2")

    owner_h = await _headers(client, owner["email"])
    member_h = await _headers(client, member["email"])
    project = await _create_project(client, owner_h)
    member_id = (await client.get("/api/v1/users/me", headers=member_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "viewer"},
        headers=owner_h,
    )
    resp2 = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "editor"},
        headers=owner_h,
    )
    assert resp2.status_code == 409, "Miembro duplicado debe retornar 409"
    assert resp2.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_remover_miembro_es_soft_delete(client, db_session):
    owner = await _register_and_verify(client, "mo3@test.dev", "memown3")
    member = await _register_and_verify(client, "mm3@test.dev", "newmem3")

    owner_h = await _headers(client, owner["email"])
    member_h = await _headers(client, member["email"])
    project = await _create_project(client, owner_h)
    member_id = (await client.get("/api/v1/users/me", headers=member_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "viewer"},
        headers=owner_h,
    )
    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{member_id}",
        headers=owner_h,
    )
    assert resp.status_code == 204, "Remover miembro debe retornar 204"

    # Registro persiste con removed_at en DB
    result = await db_session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == UUID(project["id"]),
            ProjectMember.user_id == UUID(member_id),
        )
    )
    pm = result.scalar_one_or_none()
    assert pm is not None, "Registro de membresía debe persistir (soft delete)"
    assert pm.removed_at is not None, "removed_at debe estar establecido"


@pytest.mark.asyncio
async def test_no_se_puede_remover_al_owner(client, db_session):
    owner = await _register_and_verify(client, "mo4@test.dev", "memown4")
    admin = await _register_and_verify(client, "adm5@test.dev", "sysadm5")
    await _set_role(db_session, admin["email"], "admin")

    owner_h = await _headers(client, owner["email"])
    admin_h = await _headers(client, admin["email"])
    project = await _create_project(client, owner_h)
    owner_id = (await client.get("/api/v1/users/me", headers=owner_h)).json()["id"]

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{owner_id}",
        headers=admin_h,
    )
    assert resp.status_code == 409, "No se puede remover al owner"
    assert resp.json()["error"]["code"] == "CANNOT_REMOVE_OWNER"


@pytest.mark.asyncio
async def test_historial_incluye_miembros_removidos(client):
    owner = await _register_and_verify(client, "mo5@test.dev", "memown5")
    member = await _register_and_verify(client, "mm5@test.dev", "newmem5")

    owner_h = await _headers(client, owner["email"])
    member_h = await _headers(client, member["email"])
    project = await _create_project(client, owner_h)
    member_id = (await client.get("/api/v1/users/me", headers=member_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "viewer"},
        headers=owner_h,
    )
    await client.delete(
        f"/api/v1/projects/{project['id']}/members/{member_id}",
        headers=owner_h,
    )

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/members/history",
        headers=owner_h,
    )
    assert resp.status_code == 200
    all_ids = [m["user_id"] for m in resp.json()["items"]]
    assert member_id in all_ids, "Historial debe incluir al miembro removido"


# ─────────────────────────────────────────────────────────────────────────────
# E03 — Transferencia de ownership (ART-11 · R-0304 · DU-02)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transferir_ownership_exitoso(client, db_session):
    owner = await _register_and_verify(client, "ot1@test.dev", "owntr1")
    new_owner = await _register_and_verify(client, "no1@test.dev", "newown1")

    owner_h = await _headers(client, owner["email"])
    new_owner_h = await _headers(client, new_owner["email"])
    project = await _create_project(client, owner_h)
    new_owner_id = (await client.get("/api/v1/users/me", headers=new_owner_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": new_owner_id, "role": "editor"},
        headers=owner_h,
    )
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/transfer-ownership",
        json={"new_owner_id": new_owner_id},
        headers=owner_h,
    )
    assert resp.status_code == 200, f"transferencia falló: {resp.text}"

    # Verificar en DB que el nuevo owner tiene rol owner
    result = await db_session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == UUID(project["id"]),
            ProjectMember.user_id == UUID(new_owner_id),
            ProjectMember.removed_at.is_(None),
        )
    )
    pm = result.scalar_one_or_none()
    assert pm is not None and pm.role == "owner", "Nuevo owner debe tener rol owner"


@pytest.mark.asyncio
async def test_owner_anterior_queda_como_editor(client, db_session):
    owner = await _register_and_verify(client, "ot2@test.dev", "owntr2")
    new_owner = await _register_and_verify(client, "no2@test.dev", "newown2")

    owner_h = await _headers(client, owner["email"])
    new_owner_h = await _headers(client, new_owner["email"])
    project = await _create_project(client, owner_h)
    owner_id = (await client.get("/api/v1/users/me", headers=owner_h)).json()["id"]
    new_owner_id = (await client.get("/api/v1/users/me", headers=new_owner_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": new_owner_id, "role": "editor"},
        headers=owner_h,
    )
    await client.post(
        f"/api/v1/projects/{project['id']}/transfer-ownership",
        json={"new_owner_id": new_owner_id},
        headers=owner_h,
    )

    result = await db_session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == UUID(project["id"]),
            ProjectMember.user_id == UUID(owner_id),
            ProjectMember.removed_at.is_(None),
        )
    )
    pm = result.scalar_one_or_none()
    assert pm is not None and pm.role == "editor", "Owner anterior debe quedar como editor"


@pytest.mark.asyncio
async def test_solo_owner_puede_transferir(client):
    owner = await _register_and_verify(client, "ot3@test.dev", "owntr3")
    editor = await _register_and_verify(client, "ed3@test.dev", "editortr3")

    owner_h = await _headers(client, owner["email"])
    editor_h = await _headers(client, editor["email"])
    project = await _create_project(client, owner_h)
    owner_id = (await client.get("/api/v1/users/me", headers=owner_h)).json()["id"]
    editor_id = (await client.get("/api/v1/users/me", headers=editor_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": editor_id, "role": "editor"},
        headers=owner_h,
    )
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/transfer-ownership",
        json={"new_owner_id": owner_id},
        headers=editor_h,
    )
    assert resp.status_code == 403, "Editor no puede transferir ownership"


@pytest.mark.asyncio
async def test_no_miembro_no_puede_recibir_ownership(client):
    owner = await _register_and_verify(client, "ot4@test.dev", "owntr4")
    stranger = await _register_and_verify(client, "st4@test.dev", "stranger4")

    owner_h = await _headers(client, owner["email"])
    stranger_h = await _headers(client, stranger["email"])
    project = await _create_project(client, owner_h)
    stranger_id = (await client.get("/api/v1/users/me", headers=stranger_h)).json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/transfer-ownership",
        json={"new_owner_id": stranger_id},
        headers=owner_h,
    )
    assert resp.status_code == 404, "No-miembro no puede recibir ownership"


@pytest.mark.asyncio
async def test_no_se_puede_transferir_a_si_mismo(client):
    owner = await _register_and_verify(client, "ot5@test.dev", "owntr5")
    owner_h = await _headers(client, owner["email"])
    project = await _create_project(client, owner_h)
    owner_id = (await client.get("/api/v1/users/me", headers=owner_h)).json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/transfer-ownership",
        json={"new_owner_id": owner_id},
        headers=owner_h,
    )
    assert resp.status_code == 409, "No se puede transferir ownership a uno mismo"


# ─────────────────────────────────────────────────────────────────────────────
# Seguridad — escalada de privilegios (riesgo crítico del kick-off)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_editor_no_puede_asignar_rol_owner(client):
    """Editor no puede agregar a alguien con rol owner — escalada de privilegios."""
    owner = await _register_and_verify(client, "pe1@test.dev", "privesc1")
    editor = await _register_and_verify(client, "pe2@test.dev", "privesc2")
    victim = await _register_and_verify(client, "pe3@test.dev", "privesc3")

    owner_h = await _headers(client, owner["email"])
    editor_h = await _headers(client, editor["email"])
    victim_h = await _headers(client, victim["email"])
    project = await _create_project(client, owner_h)

    editor_id = (await client.get("/api/v1/users/me", headers=editor_h)).json()["id"]
    victim_id = (await client.get("/api/v1/users/me", headers=victim_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": editor_id, "role": "editor"},
        headers=owner_h,
    )
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": victim_id, "role": "owner"},
        headers=editor_h,
    )
    assert resp.status_code == 403, "Editor no puede asignar rol owner"
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_viewer_no_puede_agregar_miembros(client):
    owner = await _register_and_verify(client, "pe4@test.dev", "privesc4")
    viewer = await _register_and_verify(client, "pe5@test.dev", "privesc5")
    victim = await _register_and_verify(client, "pe6@test.dev", "privesc6")

    owner_h = await _headers(client, owner["email"])
    viewer_h = await _headers(client, viewer["email"])
    victim_h = await _headers(client, victim["email"])
    project = await _create_project(client, owner_h)

    viewer_id = (await client.get("/api/v1/users/me", headers=viewer_h)).json()["id"]
    victim_id = (await client.get("/api/v1/users/me", headers=victim_h)).json()["id"]

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": viewer_id, "role": "viewer"},
        headers=owner_h,
    )
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": victim_id, "role": "viewer"},
        headers=viewer_h,
    )
    assert resp.status_code == 403, "Viewer no puede agregar miembros"


# ─────────────────────────────────────────────────────────────────────────────
# E02 — forgot/reset password (ART-05 · R-0205)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_siempre_200_aunque_email_no_exista(client):
    """No revela si el email existe — siempre 200."""
    resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "fantasma@test.dev"},
    )
    assert resp.status_code == 200, "forgot-password siempre retorna 200"


@pytest.mark.asyncio
async def test_forgot_password_email_existente_retorna_200(client):
    user = await _register_and_verify(client, "fp1@test.dev", "fpuser1")

    resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": user["email"]},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_flujo_completo_reset_password(client):
    """forgot → capturar token → reset → login nueva contraseña → login vieja falla."""
    user = await _register_and_verify(client, "fp2@test.dev", "fpuser2")
    token = await _get_reset_token(client, user["email"])

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NuevaClave1!"},
    )
    assert resp.status_code == 200, f"reset falló: {resp.text}"

    login_nuevo = await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": "NuevaClave1!"},
    )
    assert login_nuevo.status_code == 200, "Login con nueva contraseña debe funcionar"

    login_viejo = await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": "Test1234!"},
    )
    assert login_viejo.status_code == 401, "Login con contraseña vieja debe fallar"


@pytest.mark.asyncio
async def test_token_reset_es_de_un_solo_uso(client):
    """Segundo uso del mismo token → error."""
    user = await _register_and_verify(client, "fp3@test.dev", "fpuser3")
    token = await _get_reset_token(client, user["email"])

    await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NuevaClave1!"},
    )
    resp2 = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "OtraClave2!"},
    )
    assert resp2.status_code in (400, 401), "Segundo uso del token debe fallar"


@pytest.mark.asyncio
async def test_reset_revoca_todos_los_refresh_tokens(client):
    """Después del reset, el refresh token anterior queda revocado."""
    user = await _register_and_verify(client, "fp4@test.dev", "fpuser4")

    # Login para generar refresh token en cookie
    await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": "Test1234!"},
    )

    token = await _get_reset_token(client, user["email"])
    await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NuevaClave1!"},
    )

    # El refresh anterior (en cookie httponly) debe estar revocado
    refresh_resp = await client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code in (401, 403), "Refresh anterior debe estar revocado"