# app/repositories/base.py
from typing import Any, Generic, TypeVar
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


# ── Protocol que garantiza que el modelo tiene campo id ──
class HasId(Protocol):
    id: Any


# ── TypeVar restringido a modelos con id ──────────────────
ModelType = TypeVar("ModelType", bound=HasId)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> ModelType | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs: Any) -> ModelType:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj