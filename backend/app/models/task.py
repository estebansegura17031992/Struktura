"""Modelos SQLAlchemy — tareas, asignados, tiempo, comentarios y menciones (E04/E05/E07)."""
import uuid
from datetime import date, datetime
 
from sqlalchemy import (Boolean, CheckConstraint, ForeignKey, Integer,
                        String, Text, Date, TIMESTAMP, UniqueConstraint, text)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
 
from app.db.base import Base
 
# create_type=False — ENUMs ya existen en la DB (creados por Alembic)
TaskPriorityEnum = ENUM("low", "medium", "high",                    name="task_priority",  create_type=False)
TaskStatusEnum   = ENUM("abierto", "en_proceso", "completo",        name="task_status",    create_type=False)
MentionTypeEnum  = ENUM("user", "task",                             name="mention_type",   create_type=False)
 
 
class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("task_number", name="tasks_task_number_uk"),
        CheckConstraint("LENGTH(TRIM(title)) > 0", name="tasks_title_not_empty"),
        CheckConstraint("description IS NULL OR LENGTH(description) <= 2000",
                        name="tasks_description_len"),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    task_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("nextval('task_number_seq')"), unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(TaskPriorityEnum, nullable=False)
    status: Mapped[str] = mapped_column(TaskStatusEnum, nullable=False, server_default="abierto")
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timer_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
 
 
class TaskAssignee(Base):
    __tablename__ = "task_assignees"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="ta_task_user_uk"),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
 
 
class TaskTimeEntry(Base):
    __tablename__ = "task_time_entries"
    __table_args__ = (
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0",
                        name="tte_duration_positive"),
        CheckConstraint("stopped_at IS NULL OR stopped_at >= started_at",
                        name="tte_stopped_after_started"),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
 
 
class TaskComment(Base):
    __tablename__ = "task_comments"
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    edited_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
 
 
class CommentMention(Base):
    __tablename__ = "comment_mentions"
    __table_args__ = (
        CheckConstraint(
            "(mention_type = 'user' AND mentioned_user_id IS NOT NULL AND mentioned_task_id IS NULL)"
            " OR (mention_type = 'task' AND mentioned_task_id IS NOT NULL AND mentioned_user_id IS NULL)",
            name="cm_user_xor_task"
        ),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_comments.id", ondelete="CASCADE"))
    mention_type: Mapped[str] = mapped_column(MentionTypeEnum, nullable=False)
    mentioned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    mentioned_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))