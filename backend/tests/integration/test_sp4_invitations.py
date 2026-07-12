"""
Tests de integración — Sprint 4 · E03 (invitaciones) · Objetivos 7, 8, 9

Mismo patrón que test_sp4_timers.py / test_e04_tasks.py: funciones planas,
fixtures de conftest.py, helpers locales no compartidos entre archivos.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectInvitation, ProjectMember
from app.models.user import User
from app.services.invitation_service import InvitationService

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
    assert resp.status_code == 201, f"register fallo: {resp.text}"
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
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _set_role(db: AsyncSession, email: str, role: str) -> None:
    await db.execute(update(User).where(User.email == email).values(role=role))
    await db.commit()


async def _create_project(
    client: AsyncClient, headers: dict, name: str = "Proyecto Invitaciones"
) -> dict:
    resp = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"create_project fallo: {resp.text}"
    return resp.json()


async def _invite(
    client: AsyncClient, owner_headers: dict, project_id: str, email: str, role: str
):
    with patch(
        "app.services.invitation_service.send_project_invitation_email"
    ) as mock_send:
        mock_send.return_value = None
        resp = await client.post(
            f"/api/v1/projects/{project_id}/invitations",
            json={"email": email, "role": role},
            headers=owner_headers,
        )
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 7 — crear invitación
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_puede_invitar(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "iowner@test.dev", "iowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    resp = await _invite(
        client, owner_headers, project["id"], "invitado@test.dev", "editor"
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "invitado@test.dev"
    assert body["role"] == "editor"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_editor_no_puede_invitar(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "iowner2@test.dev", "iowner2")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    await _register_and_verify(client, "ieditor@test.dev", "ieditor")
    editor_id_resp = await client.get(
        "/api/v1/users/me", headers=await _headers(client, "ieditor@test.dev")
    )
    editor_id = editor_id_resp.json()["id"]
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": editor_id, "role": "editor"},
        headers=owner_headers,
    )
    editor_headers = await _headers(client, "ieditor@test.dev")

    resp = await _invite(
        client, editor_headers, project["id"], "otro@test.dev", "viewer"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invitar_como_owner_es_rechazado_por_schema(
    client: AsyncClient, db_session
):
    owner = await _register_and_verify(client, "iowner3@test.dev", "iowner3")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    resp = await _invite(client, owner_headers, project["id"], "otro@test.dev", "owner")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_no_permite_invitacion_pendiente_duplicada(
    client: AsyncClient, db_session
):
    owner = await _register_and_verify(client, "iowner4@test.dev", "iowner4")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    first = await _invite(
        client, owner_headers, project["id"], "dup@test.dev", "viewer"
    )
    assert first.status_code == 201

    second = await _invite(
        client, owner_headers, project["id"], "dup@test.dev", "viewer"
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INVITATION_ALREADY_PENDING"


@pytest.mark.asyncio
async def test_no_invita_a_usuario_ya_miembro(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "iowner5@test.dev", "iowner5")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    await _register_and_verify(client, "yamiembro@test.dev", "yamiembro")
    member_id = (
        await client.get(
            "/api/v1/users/me", headers=await _headers(client, "yamiembro@test.dev")
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": member_id, "role": "viewer"},
        headers=owner_headers,
    )

    resp = await _invite(
        client, owner_headers, project["id"], "yamiembro@test.dev", "editor"
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_rate_limit_10_invitaciones_por_dia(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "iowner6@test.dev", "iowner6")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    for i in range(10):
        resp = await _invite(
            client, owner_headers, project["id"], f"user{i}@test.dev", "viewer"
        )
        assert resp.status_code == 201, f"invitación {i} falló: {resp.text}"

    eleventh = await _invite(
        client, owner_headers, project["id"], "user11@test.dev", "viewer"
    )
    assert eleventh.status_code == 429
    assert eleventh.json()["error"]["code"] == "INVITATION_RATE_LIMIT_EXCEEDED"


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 8 — aceptar / rechazar
# ─────────────────────────────────────────────────────────────────────────────


async def _invite_and_get_raw_token(
    client: AsyncClient, owner_headers: dict, project_id: str, email: str, role: str
) -> str:
    """El token crudo solo se ve en el email — se captura interceptando
    send_project_invitation_email (mismo patrón que _register captura el
    código de verificación)."""
    captured = {}

    async def fake_send(to, project_name, inviter, accept_url):
        captured["url"] = accept_url

    with patch(
        "app.services.invitation_service.send_project_invitation_email",
        side_effect=fake_send,
    ):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/invitations",
            json={"email": email, "role": role},
            headers=owner_headers,
        )
    assert resp.status_code == 201, resp.text
    return captured["url"].split("token=")[1]


@pytest.mark.asyncio
async def test_aceptar_invitacion_agrega_membresia(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "aowner@test.dev", "aowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    token = await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "aceptante@test.dev", "editor"
    )

    await _register_and_verify(client, "aceptante@test.dev", "aceptante")
    invitee_headers = await _headers(client, "aceptante@test.dev")

    resp = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=invitee_headers
    )
    assert resp.status_code == 200, resp.text

    invitee_id = (await client.get("/api/v1/users/me", headers=invitee_headers)).json()[
        "id"
    ]
    result = await db_session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == UUID(project["id"]),
            ProjectMember.user_id == UUID(invitee_id),
        )
    )
    member = result.scalar_one()
    assert member.role == "editor"

    inv_result = await db_session.execute(
        select(ProjectInvitation).where(ProjectInvitation.email == "aceptante@test.dev")
    )
    assert inv_result.scalar_one().status == "accepted"


@pytest.mark.asyncio
async def test_aceptar_con_email_distinto_403(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "mowner@test.dev", "mowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    token = await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "invitado_real@test.dev", "viewer"
    )

    await _register_and_verify(client, "otro_usuario@test.dev", "otrousuario")
    other_headers = await _headers(client, "otro_usuario@test.dev")

    resp = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=other_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "EMAIL_MISMATCH"


@pytest.mark.asyncio
async def test_aceptar_token_ya_usado_409(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "uowner@test.dev", "uowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    token = await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "usado@test.dev", "viewer"
    )
    await _register_and_verify(client, "usado@test.dev", "usadousr")
    invitee_headers = await _headers(client, "usado@test.dev")

    first = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=invitee_headers
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=invitee_headers
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INVITATION_ALREADY_USED"


@pytest.mark.asyncio
async def test_aceptar_token_expirado_410(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "eowner@test.dev", "eowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    token = await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "expirado@test.dev", "viewer"
    )
    # Forzar expiración
    await db_session.execute(
        update(ProjectInvitation)
        .where(ProjectInvitation.email == "expirado@test.dev")
        .values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )
    await db_session.commit()

    await _register_and_verify(client, "expirado@test.dev", "expiradousr")
    invitee_headers = await _headers(client, "expirado@test.dev")

    resp = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=invitee_headers
    )
    assert resp.status_code == 410
    assert resp.json()["error"]["code"] == "INVITATION_EXPIRED"


@pytest.mark.asyncio
async def test_rechazar_invitacion(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "rowner@test.dev", "rowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    token = await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "rechaza@test.dev", "viewer"
    )
    await _register_and_verify(client, "rechaza@test.dev", "rechazausr")
    invitee_headers = await _headers(client, "rechaza@test.dev")

    resp = await client.post(
        f"/api/v1/invitations/{token}/reject", headers=invitee_headers
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(ProjectInvitation).where(ProjectInvitation.email == "rechaza@test.dev")
    )
    assert result.scalar_one().status == "rejected"


@pytest.mark.asyncio
async def test_job_marca_expired_las_pendientes_vencidas(
    client: AsyncClient, db_session
):
    owner = await _register_and_verify(client, "jowner@test.dev", "jowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "vencida@test.dev", "viewer"
    )
    await db_session.execute(
        update(ProjectInvitation)
        .where(ProjectInvitation.email == "vencida@test.dev")
        .values(expires_at=datetime.now(UTC) - timedelta(hours=1))
    )
    await db_session.commit()

    service = InvitationService(db_session)
    closed = await service.close_expired_invitations()
    assert closed == 1

    result = await db_session.execute(
        select(ProjectInvitation).where(ProjectInvitation.email == "vencida@test.dev")
    )
    assert result.scalar_one().status == "expired"


# ─────────────────────────────────────────────────────────────────────────────
# Objetivo 9 — cancelar invitación
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_cancela_invitacion_pendiente(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "cowner@test.dev", "cowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    invite_resp = await _invite(
        client, owner_headers, project["id"], "cancelame@test.dev", "viewer"
    )
    invitation_id = invite_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/invitations/{invitation_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 204

    result = await db_session.execute(
        select(ProjectInvitation).where(ProjectInvitation.id == UUID(invitation_id))
    )
    assert result.scalar_one().status == "expired"


@pytest.mark.asyncio
async def test_no_se_puede_cancelar_invitacion_ya_usada(
    client: AsyncClient, db_session
):
    owner = await _register_and_verify(client, "xowner@test.dev", "xowner")
    owner_headers = await _headers(client, owner["email"])
    project = await _create_project(client, owner_headers)

    token = await _invite_and_get_raw_token(
        client, owner_headers, project["id"], "usada2@test.dev", "viewer"
    )
    await _register_and_verify(client, "usada2@test.dev", "usada2usr")
    await client.post(
        f"/api/v1/invitations/{token}/accept",
        headers=await _headers(client, "usada2@test.dev"),
    )

    inv_result = await db_session.execute(
        select(ProjectInvitation).where(ProjectInvitation.email == "usada2@test.dev")
    )
    invitation_id = inv_result.scalar_one().id

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/invitations/{invitation_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_no_owner_no_puede_cancelar_invitacion(client: AsyncClient, db_session):
    owner = await _register_and_verify(client, "yowner@test.dev", "yowner")
    owner_headers = await _headers(client, owner["email"])
    # towner-equivalente: forzar rol global no-admin explícito (ver nota en
    # test_sp4_timers.py — el primer usuario registrado en DB limpia es admin)
    await _set_role(db_session, "yowner@test.dev", "editor")
    owner_headers = await _headers(client, "yowner@test.dev")
    project = await _create_project(client, owner_headers)

    invite_resp = await _invite(
        client, owner_headers, project["id"], "target@test.dev", "viewer"
    )
    invitation_id = invite_resp.json()["id"]

    await _register_and_verify(client, "yviewer@test.dev", "yviewer")
    viewer_id = (
        await client.get(
            "/api/v1/users/me", headers=await _headers(client, "yviewer@test.dev")
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": viewer_id, "role": "viewer"},
        headers=owner_headers,
    )
    viewer_headers = await _headers(client, "yviewer@test.dev")

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/invitations/{invitation_id}",
        headers=viewer_headers,
    )
    assert resp.status_code == 403
