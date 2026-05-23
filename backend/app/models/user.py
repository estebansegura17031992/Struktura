"""Modelos SQLAlchemy — usuarios y tokens de autenticación (E01)."""
import uuid
from datetime import datetime
 
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy import TIMESTAMP, text
from sqlalchemy.dialects.postgresql import ENUM, INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
 
from app.db.base import Base
 
# Tipos ENUM — create_type=False porque ya existen en la DB (creados por Alembic)
UserRoleEnum  = ENUM("viewer", "editor", "admin",   name="user_role",   create_type=False)
 
 
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("LENGTH(username) BETWEEN 3 AND 30", name="users_username_len"),
        CheckConstraint("username ~ '^[a-zA-Z0-9_]+$'", name="users_username_alnum"),
        Index("users_email_uk", text("LOWER(email)"), unique=True),
        Index("idx_users_deleted_at", "deleted_at",
              postgresql_where=text("deleted_at IS NULL")),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(255), nullable=False, server_default="UTC")
    # ENUM explícito — sin esto SQLAlchemy envía VARCHAR y PostgreSQL rechaza el INSERT
    role: Mapped[str] = mapped_column(UserRoleEnum, nullable=False, server_default="editor")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
 
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(back_populates="user")
    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(back_populates="user")
 
 
class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
 
    user: Mapped["User"] = relationship(back_populates="verification_tokens")
 
 
class RefreshToken(Base):
    """ADR-01: sin rotación en MVP. Reutilizable hasta expiración."""
    __tablename__ = "refresh_tokens"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
 
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
 
 
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
 
    user: Mapped["User"] = relationship(back_populates="reset_tokens")