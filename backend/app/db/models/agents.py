from typing import Any, Literal

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

SessionStatus = Literal["running", "waiting_user", "paused", "completed", "failed", "cancelled"]


class AgentSession(UserScopedMixin, Base):
    """Une exécution de graphe d'agents (`status` : voir `SessionStatus`)."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_status", "user_id", "status"),)

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
    """Événement persisté d'une session ; `created_at` tient lieu d'horodatage (`ts`).

    L'unicité `(session_id, seq)` garantit une séquence sans doublon et sert d'index de relecture.
    """

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
    """Un appel LLM journalisé (modèle, tokens, latence, coût estimé).

    `session_id` n'est pas une clé étrangère : l'historique des coûts survit à la session.
    """

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
