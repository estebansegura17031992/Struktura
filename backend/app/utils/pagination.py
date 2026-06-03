"""Helper de paginación reutilizable para todos los endpoints de lista (R-0901)."""

import math
from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse

T = TypeVar("T")

MAX_PAGE_SIZE_DEFAULT = 100
MAX_PAGE_SIZE_KANBAN = 50  # máximo por columna Kanban (R-0405)


async def paginate(
    session: AsyncSession,
    query: Select,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = MAX_PAGE_SIZE_DEFAULT,
) -> PaginatedResponse:
    """
    Ejecuta la query con paginación.
    Si page_size supera max_page_size se clampea e incluye page_size_applied.
    """
    page = max(1, page)
    original_page_size = page_size
    page_size = min(page_size, max_page_size)

    # Conteo total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Items paginados
    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=list(items),
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None,
        page_size_applied=page_size if original_page_size > max_page_size else None,
    )
