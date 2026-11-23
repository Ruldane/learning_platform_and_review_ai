from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class Conversation(UserScopedMixin, Base):
    """Un fil de conversation, rattaché à son sujet et à son compte."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("user_id", "scope", "subject_id", name="uq_conversations_scope"),
    )

    scope: Mapped[str] = mapped_column(String(24))
    subject_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str | None] = mapped_column(String(120), default=None)
    lesson_ids: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")


class ConversationTurn(UserScopedMixin, Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        UniqueConstraint("thread_id", "request_id", name="uq_conversation_turns_request"),
    )

    thread_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    request_id: Mapped[str] = mapped_column(String(36))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        info={"undo_pending_session": True},
    )
    mcp_call_id: Mapped[str | None] = mapped_column(String(36), default=None)
    question: Mapped[str] = mapped_column(Text)
    passage: Mapped[str | None] = mapped_column(Text)
    passage_occurrence: Mapped[int | None]
    lesson_version: Mapped[str | None] = mapped_column(String(64), default=None)
    mode: Mapped[str | None] = mapped_column(String(16), default=None)
    lesson_ids: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    practice: Mapped[list[Any] | None] = mapped_column(default=None)
    context_notes: Mapped[dict[str, str] | None] = mapped_column(JSON, default=None)
    classmates: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    expert_speeches: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    expert_judgment: Mapped[str | None] = mapped_column(Text, default=None)
    feynman: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    strong: Mapped[bool]
    answer: Mapped[str | None] = mapped_column(Text, default=None)
    focus_outcome: Mapped[str | None] = mapped_column(String(7), default=None)
    sources: Mapped[list[Any]] = mapped_column(default=list)
