"""
Tests de integración — autenticación completa (E01).
Timezone usada: UTC — disponible en todos los sistemas sin tzdata.
"""
import pytest
from unittest.mock import patch
 
USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "timezone": "UTC",          # UTC siempre disponible sin tzdata
}
 
 
# ── Helpers ────────────────────────────────────────────────────────────────────
 
async def _register(client, payload=None):
    data = payload or USER
    captured = {}
 
    async def fake_send(email, username, code):
        captured["code"] = code
 
    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
        resp = await client.post("/api/v1/auth/register", json=data)
    assert resp.status_code == 201, f"register falló ({resp.status_code}): {resp.text}"
    return data, captured.get("code")
 
 
async def _verify(client, email, code):
    resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": code},
    )
    assert resp.status_code == 200, f"verify falló ({resp.status_code}): {resp.text}"
 
 
async def _register_and_verify(client, payload=None):
    data, code = await _register(client, payload)
    await _verify(client, data["email"], code)
    return data
 
 
async def _login(client, email=None, password=None):
    return await client.post("/api/v1/auth/login", json={
        "email": email or USER["email"],
        "password": password or USER["password"],
    })
 
 
async def _get_token(client):
    """Registra, verifica y devuelve el access token."""
    await _register_and_verify(client)
    resp = await _login(client)
    assert resp.status_code == 200, f"login falló: {resp.text}"
    return resp.json()["access_token"]
 
 
# ── R-0101: Registro ───────────────────────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_register_exitoso(client):
    await _register(client)
 
 
@pytest.mark.asyncio
async def test_register_primer_usuario_es_admin(client, db_session):
    """AG-01: primer usuario → rol admin."""
    from app.repositories.user_repository import UserRepository
    await _register(client)
    user = await UserRepository(db_session).get_by_email(USER["email"])
    assert user is not None
    assert user.role == "admin"
 
 
@pytest.mark.asyncio
async def test_register_segundo_usuario_es_editor(client, db_session):
    """AG-01: segundo usuario → rol editor."""
    from app.repositories.user_repository import UserRepository
    second = {**USER, "username": "seconduser", "email": "second@example.com"}
    await _register(client)
    await _register(client, second)
    user2 = await UserRepository(db_session).get_by_email(second["email"])
    assert user2.role == "editor"
 
 
@pytest.mark.asyncio
async def test_register_email_duplicado(client):
    await _register(client)
 
    async def fake_send(email, username, code):
        pass
 
    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
        resp = await client.post("/api/v1/auth/register", json=USER)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"
 
 
@pytest.mark.asyncio
async def test_register_username_duplicado(client):
    await _register(client)
    payload2 = {**USER, "email": "otro@example.com"}
 
    async def fake_send(email, username, code):
        pass
 
    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
        resp = await client.post("/api/v1/auth/register", json=payload2)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "USERNAME_ALREADY_EXISTS"
 
 
@pytest.mark.asyncio
async def test_register_password_sin_numero(client):
    payload = {**USER, "password": "sinNumero"}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422
 
 
@pytest.mark.asyncio
async def test_register_username_muy_corto(client):
    payload = {**USER, "username": "ab"}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422
 
 
@pytest.mark.asyncio
async def test_register_timezone_invalida(client):
    payload = {**USER, "timezone": "Zona/Inventada"}
 
    async def fake_send(email, username, code):
        pass
 
    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
        resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_TIMEZONE"
 
 
@pytest.mark.asyncio
async def test_register_timezone_mexico(client):
    """America/Mexico_City válida con tzdata instalado."""
    payload = {**USER, "timezone": "America/Mexico_City", "email": "mx@example.com", "username": "mxuser"}
 
    async def fake_send(email, username, code):
        pass
 
    with patch("app.services.auth_service.send_verification_email", side_effect=fake_send):
        resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
 
 
# ── R-0101: Verificación de email ──────────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_verify_email_exitoso(client):
    _, code = await _register(client)
    resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": USER["email"], "code": code},
    )
    assert resp.status_code == 200
 
 
@pytest.mark.asyncio
async def test_verify_email_codigo_invalido(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": USER["email"], "code": "000000"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_INVALID"
 
 
@pytest.mark.asyncio
async def test_verify_email_idempotente(client):
    _, code = await _register(client)
    await _verify(client, USER["email"], code)
    resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": USER["email"], "code": code},
    )
    assert resp.status_code == 200
 
 
# ── R-0102: Login ──────────────────────────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_login_exitoso(client):
    await _register_and_verify(client)
    resp = await _login(client)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == USER["email"]
    assert "refresh_token" in resp.cookies
 
 
@pytest.mark.asyncio
async def test_login_credenciales_incorrectas(client):
    await _register_and_verify(client)
    resp = await _login(client, password="wrongPass1")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
 
 
@pytest.mark.asyncio
async def test_login_email_no_verificado(client):
    await _register(client)
    resp = await _login(client)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
 
 
@pytest.mark.asyncio
async def test_login_access_token_da_acceso(client):
    token = await _get_token(client)
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == USER["email"]
 
 
@pytest.mark.asyncio
async def test_acceso_sin_token_retorna_401(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_INVALID"
 
 
# ── R-0103: Silent refresh ─────────────────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_refresh_retorna_nuevo_access_token(client):
    await _register_and_verify(client)
    await _login(client)
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert "access_token" in resp.json()
 
 
@pytest.mark.asyncio
async def test_refresh_sin_cookie_retorna_401(client):
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
 
 
@pytest.mark.asyncio
async def test_refresh_token_revocado_retorna_401(client):
    """ADR-01: token revocado tras logout → 401."""
    token = await _get_token(client)
    await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
 
 
# ── R-0104: Logout ─────────────────────────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_logout_exitoso(client):
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
 
 
@pytest.mark.asyncio
async def test_logout_limpia_cookie(client):
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.cookies.get("refresh_token", "") == ""
 
 
# ── R-0105: Recuperación de contraseña ─────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_forgot_password_siempre_200(client):
    resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "noexiste@example.com"},
    )
    assert resp.status_code == 200
 
 
@pytest.mark.asyncio
async def test_forgot_y_reset_flujo_completo(client):
    await _register_and_verify(client)
    captured = {}
 
    async def fake_reset(email, username, reset_url):
        captured["token"] = reset_url.split("token=")[-1]
 
    with patch("app.services.auth_service.send_reset_password_email", side_effect=fake_reset):
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": USER["email"]},
        )
 
    assert "token" in captured
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": captured["token"], "new_password": "newPass456"},
    )
    assert resp.status_code == 200
 
    resp = await _login(client, password="newPass456")
    assert resp.status_code == 200
 
 
@pytest.mark.asyncio
async def test_reset_token_invalido(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "token_falso_123", "new_password": "newPass456"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_INVALID"
 
 
@pytest.mark.asyncio
async def test_reset_password_debil(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "cualquier_token", "new_password": "sinNumero"},
    )
    assert resp.status_code == 422
 
 
# ── R-0108: Perfil de usuario ───────────────────────────────────────────────────
 
@pytest.mark.asyncio
async def test_get_me(client):
    token = await _get_token(client)
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == USER["email"]
    assert data["username"] == USER["username"]
 
 
@pytest.mark.asyncio
async def test_update_timezone_valida(client):
    token = await _get_token(client)
    resp = await client.patch(
        "/api/v1/users/me",
        json={"timezone": "Europe/Madrid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "Europe/Madrid"
 
 
@pytest.mark.asyncio
async def test_update_timezone_invalida(client):
    token = await _get_token(client)
    resp = await client.patch(
        "/api/v1/users/me",
        json={"timezone": "Zona/Invalida"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
 
 
@pytest.mark.asyncio
async def test_update_full_name(client):
    token = await _get_token(client)
    resp = await client.patch(
        "/api/v1/users/me",
        json={"full_name": "Esteban Dev"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Esteban Dev"
 
 
@pytest.mark.asyncio
async def test_change_password_exitoso(client):
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": USER["password"], "new_password": "newPass789"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resp = await _login(client, password="newPass789")
    assert resp.status_code == 200
 
 
@pytest.mark.asyncio
async def test_change_password_incorrecta(client):
    token = await _get_token(client)
    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "wrongPassword1", "new_password": "newPass789"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"