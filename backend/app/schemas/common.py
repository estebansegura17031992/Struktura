"""Schemas compartidos — paginación y respuestas genéricas (R-0901)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int
    next_page: int | None
    previous_page: int | None
    page_size_applied: int | None = None  # se incluye si se clampeo el page_size


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MessageResponse(BaseModel):
    message: str

class RegisterResponse(BaseModel):
    message: str
    user_id: str