"""Repositorio de tokens de auth — refresh, verificación, reset (R-0102..R-0105)."""
from datetime import datetime, timezone
from uuid import UUID
 
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.models.user import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.repositories.base import BaseRepository
 
 
class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)
 
    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        """ADR-01: busca token no revocado y no expirado."""
        result = await self.session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.is_revoked.is_(False),
                    RefreshToken.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar_one_or_none()
 
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Busca cualquier token (incluso revocado) — para detectar reutilización (ADR-01)."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
 
    async def revoke_token(self, token_id: UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(is_revoked=True)
        )
        await self.session.flush()
 
    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """ADR-01: si se detecta reutilización de token revocado → revocar TODOS."""
        await self.session.execute(
            update(RefreshToken)
            .where(
                and_(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            )
            .values(is_revoked=True)
        )
        await self.session.flush()
 
 
class EmailVerificationRepository(BaseRepository[EmailVerificationToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(EmailVerificationToken, session)
 
    async def get_active_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                and_(
                    EmailVerificationToken.token_hash == token_hash,
                    EmailVerificationToken.used.is_(False),
                    EmailVerificationToken.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar_one_or_none()
 
    async def count_attempts(self, user_id: UUID) -> int:
        """Cuenta tokens usados o fallidos para validar el límite de 5 intentos (R-0101)."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used.is_(False),
            )
        )
        return result.scalar_one()
 
    async def mark_used(self, token_id: UUID) -> None:
        await self.session.execute(
            update(EmailVerificationToken)
            .where(EmailVerificationToken.id == token_id)
            .values(used=True)
        )
        await self.session.flush()
 
 
class PasswordResetRepository(BaseRepository[PasswordResetToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(PasswordResetToken, session)
 
    async def get_active_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar_one_or_none()
 
    async def mark_used(self, token_id: UUID) -> None:
        await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used=True)
        )
        await self.session.flush()
