"""
Utilidades de seguridad: hashing, JWT, tokens opacos.
El frontend NUNCA envía duration_seconds — el backend lo calcula (R-0502).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
 
from jose import JWTError, jwt
from passlib.context import CryptContext
 
from app.core.config import settings
 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
 
 
# ── Passwords ──────────────────────────────────────────────────────────────────
 
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)
 
 
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
 
 
# ── JWT access token ───────────────────────────────────────────────────────────
 
def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
 
 
def decode_access_token(token: str) -> dict:
    """Raises JWTError si el token es inválido o expirado."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
 
 
# ── Refresh token opaco (ADR-01) ───────────────────────────────────────────────
 
def generate_opaque_token() -> str:
    """Genera un UUID opaco de 32 bytes. El valor crudo se envía al cliente."""
    return secrets.token_hex(32)
 
 
def hash_token(raw_token: str) -> str:
    """SHA-256 del token. Solo el hash se almacena en DB."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
 
 
# ── Códigos de verificación ────────────────────────────────────────────────────
 
def generate_verification_code() -> str:
    """Código numérico de 6 dígitos para verificación de email."""
    return f"{secrets.randbelow(1_000_000):06d}"
