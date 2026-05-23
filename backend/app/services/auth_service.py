"""
Servicio de autenticación — lógica de negocio completa Sprint 1.
Cubre R-0101, R-0102, R-0103, R-0104, R-0105.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
 
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    MaxVerificationAttemptsError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    UsernameAlreadyExistsError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    generate_verification_code,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.repositories.auth_repository import (
    EmailVerificationRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRegisterRequest
from app.services.audit_service import log_action
from app.services.email_service import send_reset_password_email, send_verification_email
from app.utils.timezone import validate_timezone
 
logger = get_logger(__name__)
 
MAX_VERIFICATION_ATTEMPTS = 5
 
 
class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)
        self.verify_repo = EmailVerificationRepository(session)
        self.reset_repo = PasswordResetRepository(session)
 
    # ── R-0101: Registro ───────────────────────────────────────────────────────
 
    async def register(self, data: UserRegisterRequest, ip: str | None = None) -> User:
        # Validar timezone IANA (AG-02)
        validate_timezone(data.timezone)
 
        # Unicidad de email y username
        if await self.user_repo.get_by_email(data.email):
            raise EmailAlreadyExistsError()
        if await self.user_repo.get_by_username(data.username):
            raise UsernameAlreadyExistsError()
 
        # AG-01: primer usuario con COUNT(users)=0 recibe rol admin
        user_count = await self.user_repo.count_active_users()
        role = "admin" if user_count == 0 else "editor"
 
        user = await self.user_repo.create(
            username=data.username.lower(),
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            timezone=data.timezone,
            role=role,
            email_verified=False,
        )
 
        # Generar código de verificación (6 dígitos)
        code = generate_verification_code()
        token_hash = hash_token(code)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
 
        await self.verify_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
 
        # Enviar email (en dev imprime en consola)
        await send_verification_email(user.email, user.username, code)
 
        await log_action(self.session, "register", user_id=user.id,
                         entity_type="user", entity_id=user.id,
                         metadata={"role_assigned": role}, ip_address=ip)
 
        await self.session.commit()
        logger.info("user_registered", user_id=str(user.id), role=role)
        return user
 
    # ── R-0101: Verificar email ────────────────────────────────────────────────
 
    async def verify_email(self, email: str, code: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise InvalidCredentialsError()
 
        if user.email_verified:
            return   # ya verificado — idempotente
 
        # Verificar intentos máximos
        attempts = await self.verify_repo.count_attempts(user.id)
        if attempts >= MAX_VERIFICATION_ATTEMPTS:
            raise MaxVerificationAttemptsError()
 
        token = await self.verify_repo.get_active_by_hash(hash_token(code))
        if not token or token.user_id != user.id:
            raise TokenInvalidError()
 
        await self.verify_repo.mark_used(token.id)
        await self.user_repo.update_fields(user.id, email_verified=True)
 
        await log_action(self.session, "email_verified", user_id=user.id,
                         entity_type="user", entity_id=user.id)
        await self.session.commit()
        logger.info("email_verified", user_id=str(user.id))
 
    # ── R-0101: Reenviar código de verificación ────────────────────────────────
 
    async def resend_verification(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email)
        # Responder 200 siempre — no revelar si el email existe (R-0105 patrón)
        if not user or user.email_verified:
            return
 
        code = generate_verification_code()
        token_hash = hash_token(code)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
 
        await self.verify_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await send_verification_email(user.email, user.username, code)
        await self.session.commit()
 
    # ── R-0102: Login ──────────────────────────────────────────────────────────
 
    async def login(
        self, email: str, password: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple[str, str]:
        """Retorna (access_token, refresh_token_raw)."""
        user = await self.user_repo.get_by_email(email)
 
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
 
        if not user.email_verified:
            raise EmailNotVerifiedError()
 
        # Generar tokens
        access_token = create_access_token(str(user.id), user.role)
 
        raw_refresh = generate_opaque_token()
        refresh_hash = hash_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
 
        await self.refresh_repo.create(
            user_id=user.id,
            token_hash=refresh_hash,
            user_agent=user_agent,
            ip_address=ip,
            expires_at=expires_at,
        )
 
        await log_action(self.session, "login", user_id=user.id,
                         entity_type="user", entity_id=user.id, ip_address=ip)
        await self.session.commit()
        logger.info("user_login", user_id=str(user.id))
        return access_token, raw_refresh
 
    # ── R-0103: Silent refresh ─────────────────────────────────────────────────
 
    async def refresh_access_token(self, raw_refresh: str) -> tuple[str, User]:
        """
        ADR-01: sin rotación. El refresh token se reutiliza hasta su expiración.
        Si se detecta reutilización de token revocado → revocar TODOS los tokens del usuario.
        Retorna (nuevo_access_token, user).
        """
        token_hash = hash_token(raw_refresh)
 
        # Buscar cualquier token (incluyendo revocados) para detectar reutilización
        token = await self.refresh_repo.get_by_hash(token_hash)
 
        if not token:
            raise TokenInvalidError()
 
        if token.is_revoked:
            # Reutilización de token revocado → revocar TODOS (ADR-01)
            await self.refresh_repo.revoke_all_for_user(token.user_id)
            await self.session.commit()
            logger.warning("refresh_token_reuse_detected", user_id=str(token.user_id))
            raise TokenRevokedError()
 
        if token.expires_at < datetime.now(timezone.utc):
            raise TokenExpiredError()
 
        user = await self.user_repo.get_by_id(token.user_id)
        if not user or user.deleted_at:
            raise TokenInvalidError()
 
        access_token = create_access_token(str(user.id), user.role)
        return access_token, user
 
    # ── R-0104: Logout ─────────────────────────────────────────────────────────
 
    async def logout(self, raw_refresh: str, user_id: UUID, ip: str | None = None) -> None:
        """Revoca solo el refresh token de la sesión actual."""
        token_hash = hash_token(raw_refresh)
        token = await self.refresh_repo.get_by_hash(token_hash)
 
        if token and not token.is_revoked:
            await self.refresh_repo.revoke_token(token.id)
 
        await log_action(self.session, "logout", user_id=user_id,
                         entity_type="user", entity_id=user_id, ip_address=ip)
        await self.session.commit()
        logger.info("user_logout", user_id=str(user_id))
 
    # ── R-0105: Recuperar contraseña ───────────────────────────────────────────
 
    async def forgot_password(self, email: str) -> None:
        """
        Siempre responde 200 — no revela si el email existe (R-0105).
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            return   # silencioso
 
        raw_token = generate_opaque_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
 
        await self.reset_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
 
        # En producción esta URL vendría de una variable de entorno FRONTEND_URL
        reset_url = f"http://localhost:5173/reset-password?token={raw_token}"
        await send_reset_password_email(user.email, user.username, reset_url)
        await self.session.commit()
 
    async def reset_password(self, raw_token: str, new_password: str) -> None:
        from app.core.security import hash_password as hp
        token_hash = hash_token(raw_token)
        token = await self.reset_repo.get_active_by_hash(token_hash)
 
        if not token:
            raise TokenInvalidError()
 
        await self.reset_repo.mark_used(token.id)
        await self.user_repo.update_fields(
            token.user_id, hashed_password=hp(new_password)
        )
        # Revocar TODOS los refresh tokens del usuario (R-0105)
        await self.refresh_repo.revoke_all_for_user(token.user_id)
 
        await log_action(self.session, "password_change", user_id=token.user_id,
                         entity_type="user", entity_id=token.user_id)
        await self.session.commit()
        logger.info("password_reset", user_id=str(token.user_id))
