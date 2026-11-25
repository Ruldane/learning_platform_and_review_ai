from typing import Any, Literal

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

SessionStatus = Literal[
    "running", "waiting_user", "paused", "completed", "failed", "cancelled", "expired"
]
OPEN_SESSION_STATES = frozenset({"running", "waiting_user", "paused"})


class AgentSession(UserScopedMixin, Base):
    """One run of an agent graph (`status`: see `SessionStatus`)."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_status", "user_id", "status"),)

    played_by: Mapped[str | None] = mapped_column(String(16), default=None)
    model_provider: Mapped[str | None] = mapped_column(String(16), default=None)
    play_delivery: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    user_delivery: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    graph: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    input: Mapped[dict[str, Any]] = mapped_column(default=dict)
    subject_type: Mapped[str | None] = mapped_column(String(32), default=None)
    subject_id: Mapped[str | None] = mapped_column(String(36), default=None)
    pending_interrupt: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    error: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)


class SessionEventRecord(UserScopedMixin, Base):
    """Persisted event of a session; `created_at` serves as the timestamp (`ts`).

    Uniqueness of `(session_id, seq)` guarantees a sequence with no duplicates and serves
    as the replay index."""

    __tablename__ = "session_events"
    __table_args__ = (UniqueConstraint("session_id", "seq", name="uq_session_events_session_seq"),)

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE")
    )
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32))
    agent: Mapped[str | None] = mapped_column(String(64), default=None)
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)


class LlmCall(UserScopedMixin, Base):
    """A logged LLM call (model, tokens, latency, estimated cost).

    `session_id` is not a foreign key: the cost history outlives the session."""

    __tablename__ = "llm_calls"
    __table_args__ = (Index("ix_llm_calls_user_created", "user_id", "created_at"),)

    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    graph: Mapped[str | None] = mapped_column(String(64), default=None)
    agent: Mapped[str | None] = mapped_column(String(64), default=None)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    # Estimated tokens (call cut: deadline, `node_timeout`, cancellation, error; D117).
    estimated: Mapped[bool] = mapped_column(default=False, server_default="0")
