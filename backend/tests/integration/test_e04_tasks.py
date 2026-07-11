"""
Tests de integración — Sprint 3 · E04 · R-0401 a R-0409

Mismo patrón que tests/integration/test_rbac_and_projects.py:
  - Funciones planas con @pytest.mark.asyncio
  - Fixtures: client, db_session, clean_tables (autouse en conftest.py)
  - Helpers locales _register_and_verify / _headers / _set_role / _create_project
    (redefinidos aquí porque el repo no comparte helpers entre archivos de test)
"""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskTimeEntry
from app.models.user import User

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — mismo estilo que test_rbac_and_projects.py
# ─────────────────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, email: str, username: str, password: str = "Test1234!") -> str:
    captured = {}

    async def fake_send(e, u, code):
        captured["code"] = code

    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
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
    assert resp.status_code == 201, f"register fallo ({resp.status_code}): {resp.text}"
    return captured["code"]


async def _verify(client: AsyncClient, email: str, code: str) -> None:
    resp = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    assert resp.status_code == 200, f"verify fallo ({resp.status_code}): {resp.text}"


async def _register_and_verify(
    client: AsyncClient, email: str, username: str, password: str = "Test1234!"
) -> dict:
    code = await _register(client, email, username, password)
    await _verify(client, email, code)
    return {"email": email, "username": username, "password": password}


async def _login(client: AsyncClient, email: str, password: str = "Test1234!") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"login fallo ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


async def _headers(client: AsyncClient, email: str, password: str = "Test1234!") -> dict:
    token = await _login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


async def _set_role(db: AsyncSession, email: str, role: str) -> None:
    await db.execute(update(User).where(User.email == email).values(role=role))
    await db.commit()


async def _me_id(client: AsyncClient, headers: dict) -> str:
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_project(client: AsyncClient, headers: dict, name: str = "Proyecto Test E04") -> dict:
    resp = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"create_project fallo ({resp.status_code}): {resp.text}"
    return resp.json()


async def _add_member(client: AsyncClient, owner_headers: dict, project_id: str, user_id: str, role: str) -> None:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": user_id, "role": role},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"add_member fallo ({resp.status_code}): {resp.text}"


async def _create_task(
    client: AsyncClient, headers: dict, project_id: str, title: str = "Tarea de prueba", **extra
) -> dict:
    body = {"title": title, "priority": "medium", "project_id": project_id, **extra}
    resp = await client.post("/api/v1/tasks", json=body, headers=headers)
    assert resp.status_code == 201, f"create_task fallo ({resp.status_code}): {resp.text}"
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# CRUD basico + RBAC heredado (Dia 3 - R-0401)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_puede_crear_tarea(client):
    owner = await _register_and_verify(client, "t1@test.dev", "t1owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)

    task = await _create_task(client, headers, project["id"])
    assert task["title"] == "Tarea de prueba"
    assert task["status"] == "abierto"
    assert task["task_number"] >= 1
    assert task["assignees"] == []


@pytest.mark.asyncio
async def test_viewer_no_puede_crear_tarea(client):
    owner = await _register_and_verify(client, "t2@test.dev", "t2owner")
    viewer = await _register_and_verify(client, "t2v@test.dev", "t2viewer")

    owner_h = await _headers(client, owner["email"])
    viewer_h = await _headers(client, viewer["email"])
    project = await _create_project(client, owner_h)
    viewer_id = await _me_id(client, viewer_h)
    await _add_member(client, owner_h, project["id"], viewer_id, "viewer")

    resp = await client.post(
        "/api/v1/tasks",
        json={"title": "No permitido", "priority": "low", "project_id": project["id"]},
        headers=viewer_h,
    )
    assert resp.status_code == 403, "Viewer no puede crear tareas"


@pytest.mark.asyncio
async def test_no_miembro_no_puede_crear_tarea(client):
    owner = await _register_and_verify(client, "t3@test.dev", "t3owner")
    stranger = await _register_and_verify(client, "t3s@test.dev", "t3stranger")

    owner_h = await _headers(client, owner["email"])
    stranger_h = await _headers(client, stranger["email"])
    project = await _create_project(client, owner_h)

    resp = await client.post(
        "/api/v1/tasks",
        json={"title": "No permitido", "priority": "low", "project_id": project["id"]},
        headers=stranger_h,
    )
    assert resp.status_code == 403, "No-miembro no puede crear tareas en el proyecto"


@pytest.mark.asyncio
async def test_viewer_puede_leer_tarea(client):
    owner = await _register_and_verify(client, "t4@test.dev", "t4owner")
    viewer = await _register_and_verify(client, "t4v@test.dev", "t4viewer")

    owner_h = await _headers(client, owner["email"])
    viewer_h = await _headers(client, viewer["email"])
    project = await _create_project(client, owner_h)
    viewer_id = await _me_id(client, viewer_h)
    await _add_member(client, owner_h, project["id"], viewer_id, "viewer")

    task = await _create_task(client, owner_h, project["id"])
    resp = await client.get(f"/api/v1/tasks/{task['id']}", headers=viewer_h)
    assert resp.status_code == 200, "Viewer puede leer tareas del proyecto"


@pytest.mark.asyncio
async def test_editar_tarea_actualiza_campos(client):
    owner = await _register_and_verify(client, "t5@test.dev", "t5owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)
    task = await _create_task(client, headers, project["id"])

    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"title": "Titulo editado", "priority": "high"},
        headers=headers,
    )
    assert resp.status_code == 200, f"update fallo: {resp.text}"
    assert resp.json()["title"] == "Titulo editado"
    assert resp.json()["priority"] == "high"


@pytest.mark.asyncio
async def test_viewer_no_puede_editar_tarea(client):
    owner = await _register_and_verify(client, "t6@test.dev", "t6owner")
    viewer = await _register_and_verify(client, "t6v@test.dev", "t6viewer")

    owner_h = await _headers(client, owner["email"])
    viewer_h = await _headers(client, viewer["email"])
    project = await _create_project(client, owner_h)
    viewer_id = await _me_id(client, viewer_h)
    await _add_member(client, owner_h, project["id"], viewer_id, "viewer")
    task = await _create_task(client, owner_h, project["id"])

    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"title": "Hackeado"}, headers=viewer_h
    )
    assert resp.status_code == 403, "Viewer no puede editar tareas"


@pytest.mark.asyncio
async def test_soft_delete_tarea(client, db_session: AsyncSession):
    owner = await _register_and_verify(client, "t7@test.dev", "t7owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)
    task = await _create_task(client, headers, project["id"])

    resp = await client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert resp.status_code == 204, "Soft delete debe retornar 204"

    get_resp = await client.get(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert get_resp.status_code == 404, "Tarea eliminada no debe ser accesible"

    result = await db_session.execute(select(Task).where(Task.id == UUID(task["id"])))
    t = result.scalar_one_or_none()
    assert t is not None and t.deleted_at is not None, "deleted_at debe estar establecido (soft delete real)"


# ─────────────────────────────────────────────────────────────────────────────
# Cambio de estado + audit log (R-0402 - R-0409)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_editor_cambia_estado(client):
    owner = await _register_and_verify(client, "t8@test.dev", "t8owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)
    task = await _create_task(client, headers, project["id"])

    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}/status", json={"status": "en_proceso"}, headers=headers
    )
    assert resp.status_code == 200, f"status update fallo: {resp.text}"
    assert resp.json()["status"] == "en_proceso"


@pytest.mark.asyncio
async def test_viewer_asignado_no_puede_cambiar_estado(client):
    """R-0402: viewer nunca puede cambiar estado, ni siquiera estando asignado."""
    owner = await _register_and_verify(client, "t9@test.dev", "t9owner")
    viewer = await _register_and_verify(client, "t9v@test.dev", "t9viewer")

    owner_h = await _headers(client, owner["email"])
    viewer_h = await _headers(client, viewer["email"])
    project = await _create_project(client, owner_h)
    viewer_id = await _me_id(client, viewer_h)
    await _add_member(client, owner_h, project["id"], viewer_id, "viewer")

    task = await _create_task(client, owner_h, project["id"], assignee_ids=[viewer_id])

    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}/status", json={"status": "en_proceso"}, headers=viewer_h
    )
    assert resp.status_code == 403, "Viewer asignado NO puede cambiar estado (regla explicita)"


@pytest.mark.asyncio
async def test_cambio_estado_registra_audit_log(client, db_session: AsyncSession):
    from app.models.audit import AuditLog

    owner = await _register_and_verify(client, "t10@test.dev", "t10owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)
    task = await _create_task(client, headers, project["id"])

    await client.patch(
        f"/api/v1/tasks/{task['id']}/status", json={"status": "completo"}, headers=headers
    )

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "task_status_change",
            AuditLog.entity_id == UUID(task["id"]),
        )
    )
    entry = result.scalar_one_or_none()
    assert entry is not None, "Debe existir un audit_log del cambio de estado"
    assert entry.extra_data["new_status"] == "completo"


# ─────────────────────────────────────────────────────────────────────────────
# Filtros, FTS y paginacion (R-0403 - R-0404 - R-0405)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listar_tareas_filtra_por_prioridad(client):
    owner = await _register_and_verify(client, "t11@test.dev", "t11owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)

    await _create_task(client, headers, project["id"], title="Alta", priority="high")
    await _create_task(client, headers, project["id"], title="Baja", priority="low")

    resp = await client.get(
        "/api/v1/tasks", params={"project_id": project["id"], "priority": "high"}, headers=headers
    )
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()["items"]]
    assert "Alta" in titles and "Baja" not in titles


@pytest.mark.asyncio
async def test_busqueda_fts_menos_de_2_caracteres_retorna_422(client):
    owner = await _register_and_verify(client, "t12@test.dev", "t12owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)

    resp = await client.get(
        "/api/v1/tasks", params={"project_id": project["id"], "search": "a"}, headers=headers
    )
    assert resp.status_code == 422, "Busqueda de 1 caracter debe retornar 422"


@pytest.mark.asyncio
async def test_busqueda_fts_encuentra_por_titulo(client):
    owner = await _register_and_verify(client, "t13@test.dev", "t13owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)

    await _create_task(client, headers, project["id"], title="Migracion de base de datos")
    await _create_task(client, headers, project["id"], title="Diseno de interfaz")

    resp = await client.get(
        "/api/v1/tasks", params={"project_id": project["id"], "search": "migracion"}, headers=headers
    )
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()["items"]]
    assert any("Migracion" in t for t in titles)


@pytest.mark.asyncio
async def test_viewer_solo_puede_filtrar_assigned_to_me(client):
    owner = await _register_and_verify(client, "t14@test.dev", "t14owner")
    viewer = await _register_and_verify(client, "t14v@test.dev", "t14viewer")

    owner_h = await _headers(client, owner["email"])
    viewer_h = await _headers(client, viewer["email"])
    project = await _create_project(client, owner_h)
    viewer_id = await _me_id(client, viewer_h)
    await _add_member(client, owner_h, project["id"], viewer_id, "viewer")

    resp_me = await client.get(
        "/api/v1/tasks", params={"project_id": project["id"], "assigned_to": "me"}, headers=viewer_h
    )
    assert resp_me.status_code == 200, "Viewer puede filtrar assigned_to=me"

    owner_id = await _me_id(client, owner_h)
    resp_other = await client.get(
        "/api/v1/tasks",
        params={"project_id": project["id"], "assigned_to": owner_id},
        headers=viewer_h,
    )
    assert resp_other.status_code == 403, "Viewer no puede filtrar por otro usuario"


# ─────────────────────────────────────────────────────────────────────────────
# Asignacion multiple + ADR-03 (R-0407)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_asignar_mas_del_maximo_retorna_422(client):
    owner = await _register_and_verify(client, "t15@test.dev", "t15owner")
    headers = await _headers(client, owner["email"])
    project = await _create_project(client, headers)
    task = await _create_task(client, headers, project["id"])

    fake_ids = [str(uuid4()) for _ in range(6)]
    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"assignee_ids": fake_ids},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "MAX_ASSIGNEES_EXCEEDED"


@pytest.mark.asyncio
async def test_adr03_detiene_timer_al_pasar_a_dos_asignados(client, db_session: AsyncSession):
    """ADR-03: al pasar de 1 a 2+ asignados con timer activo, se detiene
    automaticamente, se registra audit_log y timer_disabled queda en true."""
    owner = await _register_and_verify(client, "t16@test.dev", "t16owner")
    member2 = await _register_and_verify(client, "t16b@test.dev", "t16member2")

    owner_h = await _headers(client, owner["email"])
    member2_h = await _headers(client, member2["email"])
    project = await _create_project(client, owner_h)
    owner_id = await _me_id(client, owner_h)
    member2_id = await _me_id(client, member2_h)
    await _add_member(client, owner_h, project["id"], member2_id, "editor")

    task = await _create_task(client, owner_h, project["id"], assignee_ids=[owner_id])
    task_id = UUID(task["id"])

    from datetime import UTC, datetime

    active_entry = TaskTimeEntry(
        task_id=task_id,
        user_id=UUID(owner_id),
        started_at=datetime.now(UTC),
        stopped_at=None,
    )
    db_session.add(active_entry)
    await db_session.commit()

    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"assignee_ids": [owner_id, member2_id]},
        headers=owner_h,
    )
    assert resp.status_code == 200, f"update assignees fallo: {resp.text}"
    assert resp.json()["timer_disabled"] is True, "timer_disabled debe quedar en true con 2+ asignados"

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == active_entry.id)
    )
    entry = result.scalar_one()
    assert entry.stopped_at is not None, "El timer activo debe haberse detenido"
    assert entry.stop_reason == "multi_assignee"

    from app.models.audit import AuditLog

    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "timer_stopped_multi_assignee")
    )
    assert audit_result.scalar_one_or_none() is not None, "Debe registrarse en audit_logs"


@pytest.mark.asyncio
async def test_bajar_a_un_asignado_reactiva_timer(client):
    owner = await _register_and_verify(client, "t17@test.dev", "t17owner")
    member2 = await _register_and_verify(client, "t17b@test.dev", "t17member2")

    owner_h = await _headers(client, owner["email"])
    member2_h = await _headers(client, member2["email"])
    project = await _create_project(client, owner_h)
    owner_id = await _me_id(client, owner_h)
    member2_id = await _me_id(client, member2_h)
    await _add_member(client, owner_h, project["id"], member2_id, "editor")

    task = await _create_task(
        client, owner_h, project["id"], assignee_ids=[owner_id, member2_id]
    )
    assert task["timer_disabled"] is True, "2 asignados desde la creacion debe deshabilitar timer"

    resp = await client.patch(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"assignee_ids": [owner_id]},
        headers=owner_h,
    )
    assert resp.status_code == 200
    assert resp.json()["timer_disabled"] is False, "Al bajar a 1 asignado, timer_disabled vuelve a false"