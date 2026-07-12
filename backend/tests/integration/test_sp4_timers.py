"""
Tests de integración — Sprint 4 · E05 (cronómetro) · Objetivos 1, 2, 3, 5, 6

Mismo patrón que test_e04_tasks.py:
  - Funciones planas con @pytest.mark.asyncio (asyncio_mode="auto" en
    pyproject.toml lo hace redundante, pero se mantiene por consistencia
    con el archivo más reciente del mismo dominio)
  - Fixtures: client, db_session, session_factory, clean_tables (autouse)
  - Helpers locales — no se comparten entre archivos de test (convención del repo)
"""

import asyncio
from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskTimeEntry
from app.models.user import User
from app.repositories.timer_repository import TimerRepository
from app.services.timer_service import TimerService

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


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
    assert resp.status_code == 201, f"register fallo ({resp.status_code}): {resp.text}"
    return captured["code"]


async def _register_and_verify(
    client: AsyncClient, email: str, username: str, password: str = "Test1234!"
) -> dict:
    code = await _register(client, email, username, password)
    resp = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert resp.status_code == 200
    return {"email": email, "username": username, "password": password}


async def _headers(
    client: AsyncClient, email: str, password: str = "Test1234!"
) -> dict:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, f"login fallo: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _set_role(db: AsyncSession, email: str, role: str) -> None:
    await db.execute(update(User).where(User.email == email).values(role=role))
    await db.commit()


async def _me_id(client: AsyncClient, headers: dict) -> str:
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_project(
    client: AsyncClient, headers: dict, name: str = "Proyecto Timers"
) -> dict:
    resp = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"create_project fallo: {resp.text}"
    return resp.json()


async def _add_member(
    client: AsyncClient, owner_headers: dict, project_id: str, user_id: str, role: str
) -> None:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": user_id, "role": role},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"add_member fallo: {resp.text}"


async def _create_task(
    client: AsyncClient,
    headers: dict,
    project_id: str,
    title: str = "Tarea con timer",
    **extra,
) -> dict:
    body = {"title": title, "priority": "medium", "project_id": project_id, **extra}
    resp = await client.post("/api/v1/tasks", json=body, headers=headers)
    assert resp.status_code == 201, f"create_task fallo: {resp.text}"
    return resp.json()


async def _setup_single_assignee_task(client: AsyncClient, db_session: AsyncSession):
    """Owner crea proyecto + tarea con un único asignado (editor). Retorna
    (owner_headers, assignee_headers, project_id, task_id, assignee_id)."""
    owner = await _register_and_verify(client, "towner@test.dev", "towner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    await _register_and_verify(client, "tassignee@test.dev", "tassignee")
    assignee_headers = await _headers(client, "tassignee@test.dev")
    assignee_id = await _me_id(client, assignee_headers)
    await _add_member(client, owner_headers, project["id"], assignee_id, "editor")

    task = await _create_task(
        client, owner_headers, project["id"], assignee_ids=[assignee_id]
    )
    return owner_headers, assignee_headers, project["id"], task["id"], assignee_id


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 1 — timer/start y timer/stop
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_asignado_puede_iniciar_timer(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, assignee_id = await _setup_single_assignee_task(
        client, db_session
    )

    resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["task_id"] == task_id
    assert body["user_id"] == assignee_id
    assert body["stopped_at"] is None


@pytest.mark.asyncio
async def test_no_asignado_no_puede_iniciar_timer(client: AsyncClient, db_session):
    owner_headers, _, project_id, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    # owner es miembro del proyecto pero NO está asignado a la tarea
    resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=owner_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "NOT_ASSIGNED"


@pytest.mark.asyncio
async def test_timer_deshabilitado_con_multiples_asignados(
    client: AsyncClient, db_session
):
    owner = await _register_and_verify(client, "mowner@test.dev", "mowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers, "Proyecto multi")

    await _register_and_verify(client, "m1@test.dev", "muser1")
    m1_headers = await _headers(client, "m1@test.dev")
    m1_id = await _me_id(client, m1_headers)
    await _add_member(client, owner_headers, project["id"], m1_id, "editor")

    await _register_and_verify(client, "m2@test.dev", "muser2")
    m2_id = await _me_id(client, await _headers(client, "m2@test.dev"))
    await _add_member(client, owner_headers, project["id"], m2_id, "editor")

    task = await _create_task(
        client, owner_headers, project["id"], assignee_ids=[m1_id, m2_id]
    )

    resp = await client.post(
        f"/api/v1/tasks/{task['id']}/timer/start", headers=m1_headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "TIMER_MULTI_ASSIGNEE_DISABLED"


@pytest.mark.asyncio
async def test_iniciar_timer_detiene_el_anterior_en_otra_tarea(
    client: AsyncClient, db_session
):
    (
        owner_headers,
        assignee_headers,
        project_id,
        task_a_id,
        assignee_id,
    ) = await _setup_single_assignee_task(client, db_session)
    task_b = await _create_task(
        client, owner_headers, project_id, "Tarea B", assignee_ids=[assignee_id]
    )

    resp_a = await client.post(
        f"/api/v1/tasks/{task_a_id}/timer/start", headers=assignee_headers
    )
    assert resp_a.status_code == 201
    entry_a_id = resp_a.json()["id"]

    resp_b = await client.post(
        f"/api/v1/tasks/{task_b['id']}/timer/start", headers=assignee_headers
    )
    assert resp_b.status_code == 201, resp_b.text

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == UUID(entry_a_id))
    )
    entry_a = result.scalar_one()
    assert entry_a.stopped_at is not None
    assert entry_a.stop_reason == "new_timer_started"

    active = await client.get("/api/v1/timers/active", headers=assignee_headers)
    assert active.json()["task_id"] == task_b["id"]


@pytest.mark.asyncio
async def test_iniciar_timer_ya_activo_en_misma_tarea_409(
    client: AsyncClient, db_session
):
    _, assignee_headers, _, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    first = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "TIMER_ALREADY_ACTIVE"


@pytest.mark.asyncio
async def test_detener_timer_propio(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    await client.post(f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers)

    resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/stop", headers=assignee_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stopped_at"] is not None
    assert body["duration_seconds"] is not None
    assert body["duration_seconds"] >= 0
    assert body["stop_reason"] == "manual_stop"


@pytest.mark.asyncio
async def test_detener_timer_sin_timer_activo_404(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/stop", headers=assignee_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_concurrencia_dos_starts_no_producen_dos_timers_activos(
    client: AsyncClient, db_session, session_factory
):
    """Riesgo marcado como crítico en el planning de S4. El fixture `client`
    comparte UNA sola sesión (override en conftest.py) — dos requests HTTP
    secuenciales en el mismo test no pueden reproducir una race real de DB.
    Se prueba contra el índice único parcial `tte_one_active_per_user`
    (migración 0001) directamente, con dos sesiones/conexiones
    independientes corriendo en paralelo de verdad — esa es la garantía
    real contra dos timers activos del mismo usuario, no la lógica de
    Python en TimerService (que además la ejercitan los tests de arriba)."""
    (
        _,
        assignee_headers,
        project_id,
        task_a_id,
        assignee_id,
    ) = await _setup_single_assignee_task(client, db_session)
    task_b = await _create_task(
        client,
        await _headers(client, "towner@test.dev"),
        project_id,
        "Tarea B concurrencia",
        assignee_ids=[assignee_id],
    )

    async def _insert(task_id: str):
        async with session_factory() as session:
            repo = TimerRepository(session)
            entry = await repo.create(task_id=UUID(task_id), user_id=UUID(assignee_id))
            await session.commit()
            return entry.id

    results = await asyncio.gather(
        _insert(task_a_id), _insert(task_b["id"]), return_exceptions=True
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1, (
        f"Se esperaba exactamente 1 insert exitoso de 2 concurrentes, hubo "
        f"{len(successes)}: {results}"
    )
    assert len(failures) == 1

    result = await db_session.execute(
        select(TaskTimeEntry).where(
            TaskTimeEntry.user_id == UUID(assignee_id),
            TaskTimeEntry.stopped_at.is_(None),
        )
    )
    assert len(result.scalars().all()) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 2 — GET /timers/active
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_timers_active_retorna_null_sin_timer(client: AsyncClient, db_session):
    user = await _register_and_verify(client, "noact@test.dev", "noactuser")
    headers = await _headers(client, user["email"])
    resp = await client.get("/api/v1/timers/active", headers=headers)
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_timers_active_incluye_elapsed_seconds(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    await client.post(f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers)

    resp = await client.get("/api/v1/timers/active", headers=assignee_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == task_id
    assert "elapsed_seconds" in body
    assert body["elapsed_seconds"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 3 — historial de tiempo con scope por rol (DU-04)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_viewer_solo_ve_sus_propias_entradas(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "sowner@test.dev", "sowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers, "Proyecto scope")

    await _register_and_verify(client, "sviewer@test.dev", "sviewer")
    viewer_id = await _me_id(client, await _headers(client, "sviewer@test.dev"))
    await _add_member(client, owner_headers, project["id"], viewer_id, "viewer")

    task = await _create_task(client, owner_headers, project["id"], "Tarea scope")

    # Seed directo en DB — dos entradas cerradas de dos usuarios distintos
    # en la misma tarea (simula asignados que rotaron en el tiempo).
    owner_id = await _me_id(client, owner_headers)
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    db_session.add_all(
        [
            TaskTimeEntry(
                task_id=UUID(task["id"]),
                user_id=UUID(owner_id),
                started_at=now,
                stopped_at=now,
                duration_seconds=100,
                stop_reason="manual_stop",
            ),
            TaskTimeEntry(
                task_id=UUID(task["id"]),
                user_id=UUID(viewer_id),
                started_at=now,
                stopped_at=now,
                duration_seconds=200,
                stop_reason="manual_stop",
            ),
        ]
    )
    await db_session.commit()

    viewer_headers = await _headers(client, "sviewer@test.dev")
    resp = await client.get(
        f"/api/v1/tasks/{task['id']}/time-entries", headers=viewer_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "own"
    assert len(body["items"]) == 1
    assert body["items"][0]["user_id"] == viewer_id


@pytest.mark.asyncio
async def test_owner_ve_entradas_de_todo_el_equipo(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "aowner@test.dev", "aowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers, "Proyecto scope all")

    await _register_and_verify(client, "aviewer@test.dev", "aviewer")
    viewer_id = await _me_id(client, await _headers(client, "aviewer@test.dev"))
    await _add_member(client, owner_headers, project["id"], viewer_id, "viewer")

    task = await _create_task(client, owner_headers, project["id"], "Tarea scope all")
    owner_id = await _me_id(client, owner_headers)

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    db_session.add_all(
        [
            TaskTimeEntry(
                task_id=UUID(task["id"]),
                user_id=UUID(owner_id),
                started_at=now,
                stopped_at=now,
                duration_seconds=100,
            ),
            TaskTimeEntry(
                task_id=UUID(task["id"]),
                user_id=UUID(viewer_id),
                started_at=now,
                stopped_at=now,
                duration_seconds=200,
            ),
        ]
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/tasks/{task['id']}/time-entries", headers=owner_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "all"
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_borrar_entrada_propia_reciente(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, assignee_id = await _setup_single_assignee_task(
        client, db_session
    )
    await client.post(f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers)
    stop_resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/stop", headers=assignee_headers
    )
    entry_id = stop_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/tasks/{task_id}/time-entries/{entry_id}", headers=assignee_headers
    )
    assert resp.status_code == 204

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == UUID(entry_id))
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_borrar_entrada_de_otro_usuario_403(client: AsyncClient, db_session):
    owner_headers, assignee_headers, _, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    # towner es el primer usuario registrado en esta DB de test limpia →
    # auth_service.py lo vuelve admin automáticamente (role = "admin" if
    # user_count == 0 else "editor"). Forzamos su rol global a "editor"
    # para probar el 403 de un no-dueño-no-admin genuino, no el bypass de admin.
    await _set_role(db_session, "towner@test.dev", "editor")
    owner_headers = await _headers(client, "towner@test.dev")

    await client.post(f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers)
    stop_resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/stop", headers=assignee_headers
    )
    entry_id = stop_resp.json()["id"]

    # owner NO es dueño de la entrada y no es admin
    resp = await client.delete(
        f"/api/v1/tasks/{task_id}/time-entries/{entry_id}", headers=owner_headers
    )
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 5 — logout detiene el timer activo (atómico)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_detiene_timer_activo(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, assignee_id = await _setup_single_assignee_task(
        client, db_session
    )
    start_resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    entry_id = start_resp.json()["id"]

    logout_resp = await client.post("/api/v1/auth/logout", headers=assignee_headers)
    assert logout_resp.status_code == 200

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == UUID(entry_id))
    )
    entry = result.scalar_one()
    assert entry.stopped_at is not None
    assert entry.stop_reason == "logout"


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 6 — admin detiene el timer de cualquier usuario
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_detiene_timer_de_otro_usuario(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, assignee_id = await _setup_single_assignee_task(
        client, db_session
    )
    start_resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    entry_id = start_resp.json()["id"]

    await _register_and_verify(client, "sysadmin@test.dev", "sysadmin")
    await _set_role(db_session, "sysadmin@test.dev", "admin")
    admin_headers = await _headers(client, "sysadmin@test.dev")

    resp = await client.post(
        f"/api/v1/admin/users/{assignee_id}/timer/stop", headers=admin_headers
    )
    assert resp.status_code == 200, resp.text

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == UUID(entry_id))
    )
    entry = result.scalar_one()
    assert entry.stopped_at is not None
    assert entry.stop_reason == "admin_stop"


@pytest.mark.asyncio
async def test_admin_stop_timer_sin_timer_activo_404(client: AsyncClient, db_session):
    user = await _register_and_verify(client, "noatimer@test.dev", "noatimer")
    user_id = await _me_id(client, await _headers(client, user["email"]))

    await _register_and_verify(client, "sysadmin2@test.dev", "sysadmin2")
    await _set_role(db_session, "sysadmin2@test.dev", "admin")
    admin_headers = await _headers(client, "sysadmin2@test.dev")

    resp = await client.post(
        f"/api/v1/admin/users/{user_id}/timer/stop", headers=admin_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_no_admin_no_puede_detener_timer_ajeno(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, assignee_id = await _setup_single_assignee_task(
        client, db_session
    )
    await client.post(f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers)

    resp = await client.post(
        f"/api/v1/admin/users/{assignee_id}/timer/stop", headers=assignee_headers
    )
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 4 — job de huérfanos (cierre automático por max_timer_hours)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_job_cierra_timers_mas_viejos_que_max_timer_hours(
    client: AsyncClient, db_session
):
    """No hay endpoint HTTP para esto — es un job periódico (APScheduler).
    Se invoca TimerService.close_orphaned_timers() directo, mismo patrón
    que test_e04_tasks.py usa para exercitar reglas de ADR-03 a nivel service
    cuando no hay una ruta HTTP dedicada."""
    _, assignee_headers, _, task_id, assignee_id = await _setup_single_assignee_task(
        client, db_session
    )
    start_resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    entry_id = start_resp.json()["id"]

    # Forzar started_at 13h atrás (> default max_timer_hours=12)
    from datetime import UTC, datetime, timedelta

    old_start = datetime.now(UTC) - timedelta(hours=13)
    await db_session.execute(
        update(TaskTimeEntry)
        .where(TaskTimeEntry.id == UUID(entry_id))
        .values(started_at=old_start)
    )
    await db_session.commit()

    service = TimerService(db_session)
    closed_count = await service.close_orphaned_timers()
    assert closed_count == 1

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == UUID(entry_id))
    )
    entry = result.scalar_one()
    assert entry.stopped_at is not None
    assert entry.stop_reason == "auto_closed_max_hours"
    # Duración calculada HASTA EL LÍMITE (12h = 43200s), no hasta el cierre
    assert entry.duration_seconds == 12 * 3600


@pytest.mark.asyncio
async def test_job_no_toca_timers_dentro_del_limite(client: AsyncClient, db_session):
    _, assignee_headers, _, task_id, _ = await _setup_single_assignee_task(
        client, db_session
    )
    resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start", headers=assignee_headers
    )
    entry_id = resp.json()["id"]

    service = TimerService(db_session)
    closed_count = await service.close_orphaned_timers()
    assert closed_count == 0

    result = await db_session.execute(
        select(TaskTimeEntry).where(TaskTimeEntry.id == UUID(entry_id))
    )
    assert result.scalar_one().stopped_at is None
