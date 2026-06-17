"""
Tests de integración E03 — Sprint 2
ART-15 · R-0301 a R-0307

Cubre gaps no incluidos en test_rbac_and_projects.py:
  - my_role y member_count en GET /projects
  - user.username y user.full_name en GET /projects/{id}/members
  - PROJECT_LIMIT_REACHED
  - Paginación en GET /projects
  - Historial paginado GET /projects/{id}/members/history
  - audit_logs registra member_added y member_removed
  - Editor no puede editar proyecto (solo owner)
  - member_history acceso por rol
  - Viewer no puede ver historial

Patrón idéntico a test_rbac_and_projects.py:
  - Funciones planas con asyncio_mode="auto"
  - Fixtures: client, db_session de conftest.py
  - send_verification_email mockeado en conftest.py
"""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(
    client: AsyncClient, email: str, username: str, password: str = "Test1234!"
) -> str:
    captured = {}

    async def fake_send(e, u, code):
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
    assert resp.status_code == 201, f"register falló ({resp.status_code}): {resp.text}"
    return captured["code"]


async def _verify(client: AsyncClient, email: str, code: str) -> None:
    resp = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert resp.status_code == 200, f"verify falló ({resp.status_code}): {resp.text}"


async def _register_and_verify(
    client: AsyncClient, email: str, username: str, password: str = "Test1234!"
) -> dict:
    code = await _register(client, email, username, password)
    await _verify(client, email, code)
    return {"email": email, "username": username, "password": password}


async def _login(client: AsyncClient, email: str, password: str = "Test1234!") -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, f"login falló ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


async def _auth(client: AsyncClient, email: str, password: str = "Test1234!") -> dict:
    token = await _login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


async def _set_role(db: AsyncSession, email: str, role: str) -> None:
    from sqlalchemy import update  # noqa: PLC0415

    await db.execute(update(User).where(User.email == email).values(role=role))
    await db.commit()


async def _create_project(
    client: AsyncClient, headers: dict, name: str = "Proyecto Test"
) -> dict:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "description": "Descripción de prueba"},
        headers=headers,
    )
    assert resp.status_code == 201, f"create project falló: {resp.text}"
    return resp.json()


# ── GET /projects — my_role y member_count ────────────────────────────────────


async def test_list_projects_incluye_my_role(
    client: AsyncClient, db_session: AsyncSession
):
    """GET /projects retorna my_role en cada proyecto."""
    await _register_and_verify(client, "myrole@test.dev", "myroleusr")
    await _set_role(db_session, "myrole@test.dev", "editor")
    headers = await _auth(client, "myrole@test.dev")

    await _create_project(client, headers, "Proyecto my_role")

    resp = await client.get("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert "my_role" in items[0], "my_role no está en el response"
    assert items[0]["my_role"] == "owner"


async def test_list_projects_incluye_member_count(
    client: AsyncClient, db_session: AsyncSession
):
    """GET /projects retorna member_count en cada proyecto."""
    await _register_and_verify(client, "mcount@test.dev", "mcountusr")
    await _set_role(db_session, "mcount@test.dev", "editor")
    headers = await _auth(client, "mcount@test.dev")

    await _create_project(client, headers, "Proyecto member_count")

    resp = await client.get("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert "member_count" in items[0], "member_count no está en el response"
    assert items[0]["member_count"] >= 1  # al menos el owner


async def test_list_projects_paginacion(client: AsyncClient, db_session: AsyncSession):
    """GET /projects respeta page y page_size."""
    await _register_and_verify(client, "pagproj@test.dev", "pagprojusr")
    await _set_role(db_session, "pagproj@test.dev", "editor")
    headers = await _auth(client, "pagproj@test.dev")

    # Crear 3 proyectos
    for i in range(3):
        await _create_project(client, headers, f"Pag Proyecto {i}")

    resp = await client.get("/api/v1/projects?page=1&page_size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total"] >= 3
    assert data["next_page"] == 2


async def test_list_projects_page_2(client: AsyncClient, db_session: AsyncSession):
    """GET /projects página 2 retorna items restantes."""
    await _register_and_verify(client, "pag2proj@test.dev", "pag2projusr")
    await _set_role(db_session, "pag2proj@test.dev", "editor")
    headers = await _auth(client, "pag2proj@test.dev")

    for i in range(3):
        await _create_project(client, headers, f"Pag2 Proyecto {i}")

    resp = await client.get("/api/v1/projects?page=2&page_size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["previous_page"] == 1
    assert len(data["items"]) >= 1


# ── GET /projects/{id}/members — user info ────────────────────────────────────


async def test_list_members_incluye_username_y_full_name(
    client: AsyncClient, db_session: AsyncSession
):
    """GET /projects/{id}/members incluye user.username y user.full_name."""
    await _register_and_verify(client, "meminfo@test.dev", "meminfousr")
    await _set_role(db_session, "meminfo@test.dev", "editor")
    headers = await _auth(client, "meminfo@test.dev")

    project = await _create_project(client, headers, "Proyecto con user info")
    project_id = project["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/members", headers=headers)
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) >= 1

    member = members[0]
    assert "user" in member, "Campo user no está en MemberResponse"
    assert member["user"] is not None
    assert "username" in member["user"], "username no está en user"
    assert "full_name" in member["user"], "full_name no está en user"
    assert member["user"]["username"] == "meminfousr"


async def test_list_members_user_no_es_null_para_miembros_activos(
    client: AsyncClient, db_session: AsyncSession
):
    """user nunca es null para miembros activos."""
    await _register_and_verify(client, "usrnotnull@test.dev", "usrnotnullusr")
    await _set_role(db_session, "usrnotnull@test.dev", "editor")
    headers = await _auth(client, "usrnotnull@test.dev")

    project = await _create_project(client, headers)
    project_id = project["id"]

    # Agregar segundo miembro
    await _register_and_verify(client, "second@test.dev", "secondusr")
    result = await db_session.execute(
        select(User).where(User.email == "second@test.dev")
    )
    second_user = result.scalar_one()

    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": str(second_user.id), "role": "viewer"},
        headers=headers,
    )

    resp = await client.get(f"/api/v1/projects/{project_id}/members", headers=headers)
    assert resp.status_code == 200
    for member in resp.json():
        assert member["user"] is not None, f"user es null para member_id={member['id']}"


# ── PROJECT_LIMIT_REACHED ─────────────────────────────────────────────────────


async def test_project_limit_reached(client: AsyncClient, db_session: AsyncSession):
    """POST /projects retorna 422 PROJECT_LIMIT_REACHED al superar el límite."""
    from sqlalchemy import update  # noqa: PLC0415

    from app.models.auth import SystemSetting  # noqa: PLC0415

    await _register_and_verify(client, "limitproj@test.dev", "limitprojusr")
    await _set_role(db_session, "limitproj@test.dev", "editor")
    headers = await _auth(client, "limitproj@test.dev")

    # Bajar el límite a 1 en system_settings
    result = await db_session.execute(
        select(SystemSetting).where(SystemSetting.key == "max_projects_per_user")
    )
    setting = result.scalar_one_or_none()
    if setting:
        await db_session.execute(
            update(SystemSetting)
            .where(SystemSetting.key == "max_projects_per_user")
            .values(value="1")
        )
    else:
        db_session.add(SystemSetting(key="max_projects_per_user", value="1"))
    await db_session.commit()

    # Crear el primer proyecto (debe pasar)
    resp1 = await client.post(
        "/api/v1/projects",
        json={"name": "Primer proyecto"},
        headers=headers,
    )
    assert resp1.status_code == 201

    # Crear el segundo (debe fallar)
    resp2 = await client.post(
        "/api/v1/projects",
        json={"name": "Segundo proyecto"},
        headers=headers,
    )
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "PROJECT_LIMIT_REACHED"


# ── PATCH /projects/{id} — permisos ───────────────────────────────────────────


async def test_editor_no_puede_editar_proyecto(
    client: AsyncClient, db_session: AsyncSession
):
    """PATCH /projects/{id} retorna 403 si el usuario es editor (no owner)."""
    # Owner crea el proyecto
    await _register_and_verify(client, "editpatch@test.dev", "editpatchowner")
    await _set_role(db_session, "editpatch@test.dev", "editor")
    owner_headers = await _auth(client, "editpatch@test.dev")
    project = await _create_project(client, owner_headers, "Proyecto solo owner edita")
    project_id = project["id"]

    # Editor se agrega como miembro
    await _register_and_verify(client, "editpatchmem@test.dev", "editpatchmem")
    result = await db_session.execute(
        select(User).where(User.email == "editpatchmem@test.dev")
    )
    editor_user = result.scalar_one()

    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": str(editor_user.id), "role": "editor"},
        headers=owner_headers,
    )

    editor_headers = await _auth(client, "editpatchmem@test.dev")
    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Nombre cambiado por editor"},
        headers=editor_headers,
    )
    assert resp.status_code == 403


async def test_owner_puede_editar_nombre_y_descripcion(
    client: AsyncClient, db_session: AsyncSession
):
    """PATCH /projects/{id} actualiza nombre y descripción correctamente."""
    await _register_and_verify(client, "owneredit@test.dev", "ownerediteusr")
    await _set_role(db_session, "owneredit@test.dev", "editor")
    headers = await _auth(client, "owneredit@test.dev")

    project = await _create_project(client, headers, "Nombre original")
    project_id = project["id"]

    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Nombre actualizado", "description": "Nueva descripción"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Nombre actualizado"
    assert data["description"] == "Nueva descripción"


# ── Historial de miembros ──────────────────────────────────────────────────────


async def test_historial_paginado(client: AsyncClient, db_session: AsyncSession):
    """GET /projects/{id}/members/history soporta paginación."""
    await _register_and_verify(client, "histpag@test.dev", "histpagusr")
    await _set_role(db_session, "histpag@test.dev", "editor")
    headers = await _auth(client, "histpag@test.dev")
    project = await _create_project(client, headers)
    project_id = project["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/members/history?page=1&page_size=10",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1


async def test_viewer_no_puede_ver_historial(
    client: AsyncClient, db_session: AsyncSession
):
    """GET /projects/{id}/members/history retorna 403 para viewer."""
    # Owner crea proyecto
    await _register_and_verify(client, "histowner@test.dev", "histownerusr")
    await _set_role(db_session, "histowner@test.dev", "editor")
    owner_headers = await _auth(client, "histowner@test.dev")
    project = await _create_project(client, owner_headers)
    project_id = project["id"]

    # Viewer se une
    await _register_and_verify(client, "histviewer@test.dev", "histviewusr")
    result = await db_session.execute(
        select(User).where(User.email == "histviewer@test.dev")
    )
    viewer_user = result.scalar_one()

    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": str(viewer_user.id), "role": "viewer"},
        headers=owner_headers,
    )

    viewer_headers = await _auth(client, "histviewer@test.dev")
    resp = await client.get(
        f"/api/v1/projects/{project_id}/members/history",
        headers=viewer_headers,
    )
    assert resp.status_code == 403


# ── Audit logs ────────────────────────────────────────────────────────────────


async def test_audit_log_member_added(client: AsyncClient, db_session: AsyncSession):
    """add_member registra entrada en audit_logs con action='member_added'."""
    await _register_and_verify(client, "auditadd@test.dev", "auditaddusr")
    await _set_role(db_session, "auditadd@test.dev", "editor")
    headers = await _auth(client, "auditadd@test.dev")
    project = await _create_project(client, headers)
    project_id = project["id"]

    # Nuevo usuario a agregar
    await _register_and_verify(client, "newmember@test.dev", "newmemberusr")
    result = await db_session.execute(
        select(User).where(User.email == "newmember@test.dev")
    )
    new_user = result.scalar_one()

    resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": str(new_user.id), "role": "viewer"},
        headers=headers,
    )
    assert resp.status_code == 201

    # Verificar audit_log
    log_result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "member_added",
            AuditLog.entity_type == "project",
        )
    )
    log = log_result.scalars().first()
    assert log is not None, "No se registró audit_log para member_added"
    assert log.extra_data is not None
    # Las claves del extra_data las define audit_service.log_action
    # El service guarda: added_user_id, role en metadata del log_action
    # Verificar que el log existe con la acción correcta es suficiente
    assert log.action == "member_added"
    assert str(log.entity_id) == project_id


async def test_audit_log_member_removed(client: AsyncClient, db_session: AsyncSession):
    """remove_member registra entrada en audit_logs con action='member_removed'."""
    await _register_and_verify(client, "auditrem@test.dev", "auditremusr")
    await _set_role(db_session, "auditrem@test.dev", "editor")
    headers = await _auth(client, "auditrem@test.dev")
    project = await _create_project(client, headers)
    project_id = project["id"]

    # Agregar miembro
    await _register_and_verify(client, "toremove@test.dev", "toremoveusr")
    result = await db_session.execute(
        select(User).where(User.email == "toremove@test.dev")
    )
    to_remove = result.scalar_one()

    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": str(to_remove.id), "role": "editor"},
        headers=headers,
    )

    # Remover miembro
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/members/{to_remove.id}",
        headers=headers,
    )
    assert resp.status_code == 204

    # Verificar audit_log
    log_result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "member_removed",
            AuditLog.entity_type == "project",
        )
    )
    log = log_result.scalars().first()
    assert log is not None, "No se registró audit_log para member_removed"
    assert log.action == "member_removed"
    assert str(log.entity_id) == project_id


async def test_audit_log_ownership_transferred(
    client: AsyncClient, db_session: AsyncSession
):
    """transfer_ownership registra entrada en audit_logs."""
    await _register_and_verify(client, "auditowner@test.dev", "auditownerusr")
    await _set_role(db_session, "auditowner@test.dev", "editor")
    headers = await _auth(client, "auditowner@test.dev")
    project = await _create_project(client, headers)
    project_id = project["id"]

    # Agregar nuevo owner como miembro
    await _register_and_verify(client, "newowner@test.dev", "newownerusr")
    result = await db_session.execute(
        select(User).where(User.email == "newowner@test.dev")
    )
    new_owner = result.scalar_one()

    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": str(new_owner.id), "role": "editor"},
        headers=headers,
    )

    # Transferir
    resp = await client.post(
        f"/api/v1/projects/{project_id}/transfer-ownership",
        json={"new_owner_id": str(new_owner.id)},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verificar audit_log
    log_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "ownership_transferred")
    )
    log = log_result.scalars().first()
    assert log is not None, "No se registró audit_log para ownership_transferred"
    assert log.action == "ownership_transferred"
    assert str(log.entity_id) == project_id
