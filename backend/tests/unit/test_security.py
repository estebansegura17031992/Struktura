# tests/unit/test_security.py
import pytest
from app.core.security import decode_access_token, create_access_token, hash_password, verify_password
from app.core.exceptions import TokenInvalidError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    password = "MiContraseña123!"
    hashed = hash_password(password)

    assert hashed != password  # no está en texto plano
    assert verify_password(password, hashed)  # verifica correctamente
    assert not verify_password("wrong", hashed)  # rechaza contraseña incorrecta


def test_access_token_encode_decode():
    payload = {"user_id": "usr_abc123", "role": "editor"}
    token = create_access_token(payload)

    decoded = decode_access_token(token)
    assert decoded["user_id"] == "usr_abc123"
    assert decoded["role"] == "editor"
    assert "exp" in decoded


def test_access_token_invalid_raises():
    import pytest

    with pytest.raises(TokenInvalidError):
        decode_access_token("token.invalido.aqui")
