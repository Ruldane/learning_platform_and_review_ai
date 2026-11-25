"""Standalone exercises, frozen on a published chapter."""

from typing import Any, Literal

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

type HuntStage = Literal["preparing", "ready", "reviewing", "complete"]


class LessonHunt(UserScopedMixin, Base):
    __tablename__ = "lesson_hunts"

    lesson_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    source: Mapped[str] = mapped_column(Text)
    stage: Mapped[HuntStage] = mapped_column(String(12))
    session_id: Mapped[str] = mapped_column(String(36))
    exercise: Mapped[str | None] = mapped_column(Text)
    errors: Mapped[dict[str, Any] | None]
    responses: Mapped[list[str] | None] = mapped_column(JSON)
    assessment: Mapped[dict[str, Any] | None]
