"""Repositorio de usuarios — queries de DB (sin lógica de negocio)."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(
                func.lower(User.email) == email.lower(),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.username == username.lower(),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def count_active_users(self) -> int:
        """Usado para determinar si el primer registro recibe rol admin (AG-01)."""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def update_fields(self, user_id: UUID, **fields) -> User | None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(**fields)
        )
        await self.session.flush()
        return await self.get_by_id(user_id)
