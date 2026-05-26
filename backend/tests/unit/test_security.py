# tests/unit/test_security.py
import pytest
from jose.exceptions import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_verification_code,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_and_verify():
    password = "MiContraseña123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_password_bcrypt_cost():
    """El hash debe usar bcrypt — empieza con $2b$12$."""
    hashed = hash_password("cualquier_password")
    assert hashed.startswith("$2b$12$")


def test_access_token_encode_decode():
    """create_access_token recibe user_id y role por separado."""
    token = create_access_token(user_id="usr_abc123", role="editor")
    decoded = decode_access_token(token)

    assert decoded["sub"] == "usr_abc123"
    assert decoded["role"] == "editor"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_access_token_invalid_raises():
    """decode_access_token lanza JWTError ante un token inválido."""
    with pytest.raises(JWTError):
        decode_access_token("token.invalido.aqui")


def test_hash_token_is_deterministic():
    """El mismo token siempre produce el mismo hash."""
    raw = "mi_refresh_token_opaco"
    assert hash_token(raw) == hash_token(raw)


def test_hash_token_is_different_from_raw():
    raw = "mi_refresh_token_opaco"
    assert hash_token(raw) != raw


def test_verification_code_format():
    """El código debe ser numérico de exactamente 6 dígitos."""
    code = generate_verification_code()
    assert len(code) == 6
    assert code.isdigit()