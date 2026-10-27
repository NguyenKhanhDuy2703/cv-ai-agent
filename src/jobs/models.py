"""AI-owned PostgreSQL tables; independent of Render's storage."""
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA_REVISION = "0001_generation_jobs"
TERMINAL_STATUSES = frozenset({"NEEDS_INPUT", "COMPLETED", "FAILED"})
TERMINAL_EVENTS = frozenset({"needs_input", "done", "error"})


class Base(DeclarativeBase):
    pass


class GenerationJob(Base):
    __tablename__ = "ai_generation_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('QUEUED','RUNNING','NEEDS_INPUT','COMPLETED','FAILED')", name="valid_job_status"),
        Index("ix_ai_jobs_queue", "status", "created_at"),
        Index("ix_ai_jobs_expiry", "expires_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(Text, unique=True)
    generation_id: Mapped[str] = mapped_column(Text, unique=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[dict[str, str] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GenerationEvent(Base):
    __tablename__ = "ai_generation_events"
    __table_args__ = (
        UniqueConstraint("job_id", "sequence", name="uq_ai_event_sequence"),
        Index("uq_ai_event_terminal", "job_id", unique=True,
              postgresql_where=text("type IN ('done','needs_input','error')")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("ai_generation_jobs.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    attempt: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
