from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class LessonUpdate(UserScopedMixin, Base):
    __tablename__ = "lesson_updates"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", "library", "version"),)

    lesson_id: Mapped[str] = mapped_column(String(36), ForeignKey("lessons.id", ondelete="CASCADE"))
    library: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str] = mapped_column(String(2000))
    base_hash: Mapped[str] = mapped_column(String(64), info={"export": False})
    detected: Mapped[list[Any]]
    preparation_session_id: Mapped[str] = mapped_column(String(36))
    draft: Mapped[dict[str, Any] | None]
    publication_session_id: Mapped[str | None] = mapped_column(String(36))
