"""
PasswordService — Recuperación de contraseña
Sprint 2 · ART-05 · R-0205

Flujo:
  1. forgot_password  → genera token UUID, lo hashea, envía email, retorna 200 siempre
  2. reset_password   → valida token, actualiza contraseña, invalida token + refresh tokens

Reglas de seguridad (revisión Security Día 5):
  - Token expira en 1 hora exacta
  - Token es de un solo uso — marcado como usado en la misma transacción
  - Si el email no existe → 200 igual (no revelar existencia de cuenta)
  - Al resetear: revocar TODOS los refresh tokens activos del usuario
  - Nunca loggear el token en texto plano
  - Rate limiting en el router: 3 req/IP/15min (ya configurado en auth.py)
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import structlog
from fastapi import HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import PasswordResetToken, RefreshToken, User
from app.services.email_service import send_reset_password_email

logger = structlog.get_logger(__name__)

TOKEN_EXPIRY_HOURS = 1


def _hash_token(raw_token: str) -> str:
    """SHA-256 del token. El raw token viaja por email; solo el hash se guarda en DB."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


class PasswordService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def forgot_password(self, email: str) -> None:
        """
        Genera token de reset y envía email.
        Siempre retorna None (200 al caller) — no revelar si el email existe.
        R-0205
        """
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.info(
                "password.reset_requested_unknown_email",
                email_hash=_hash_token(email),
            )
            return  # 200 silencioso — no revelar existencia de cuenta

        # Invalidar tokens anteriores no usados del mismo usuario
        await self.db.execute(
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > datetime.now(UTC),
                )
            )
            .values(used=True)
        )

        # Generar token de un solo uso
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRY_HOURS)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            used=False,
        )
        self.db.add(reset_token)
        await self.db.flush()

        # Enviar email (EMAIL_DEV_MODE en CI — no consume cuota Resend)
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={raw_token}"
        await send_reset_password_email(
            email=user.email,
            username=user.full_name or user.username,
            reset_url=reset_url,
        )

        await self.db.commit()
        logger.info("password.reset_email_sent", user_id=str(user.id))

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        """
        Valida el token y actualiza la contraseña.
        Operación atómica: marcar token como usado + actualizar password +
        revocar refresh tokens — todo en la misma transacción.
        R-0205
        """
        token_hash = _hash_token(raw_token)
        now = datetime.now(UTC)

        # Buscar token válido (no usado, no expirado)
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > now,
                )
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            # Verificar si existió pero ya fue usado (para dar 410 Gone)
            result_used = await self.db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.token_hash == token_hash
                )
            )
            used = result_used.scalar_one_or_none()
            if used and used.used is True:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail={
                        "error": {
                            "code": "TOKEN_ALREADY_USED",
                            "message": "Este enlace de recuperación ya fue utilizado. Solicita uno nuevo.",
                        }
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_OR_EXPIRED_TOKEN",
                        "message": "El enlace de recuperación es inválido o ha expirado. Solicita uno nuevo.",
                    }
                },
            )

        assert reset_token is not None  # garantiza tipo para mypy

        # Obtener usuario — variable separada para evitar confusión de tipos en mypy
        user_result = await self.db.execute(
            select(User).where(User.id == reset_token.user_id)
        )
        user = user_result.scalar_one()

        # Validar nueva contraseña
        if len(new_password) < 8 or not any(c.isdigit() for c in new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "La contraseña debe tener al menos 8 caracteres y un número.",
                    }
                },
            )

        # ── Operación atómica ──────────────────────────────────────────────────

        # 1. Marcar token como usado
        reset_token.used = True

        # 2. Actualizar contraseña (bcrypt cost 12 — mismo que en registro S1)
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12))
        user.hashed_password = hashed.decode()

        # 3. Revocar TODOS los refresh tokens activos del usuario
        await self.db.execute(
            update(RefreshToken)
            .where(
                and_(
                    RefreshToken.user_id == user.id,
                    RefreshToken.is_revoked.is_(False),
                )
            )
            .values(is_revoked=True)
        )

        await self.db.commit()

        logger.info(
            "password.reset_completed",
            user_id=str(user.id),
            tokens_revoked=True,
        )
