from sqlalchemy import JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class LessonVariantSet(UserScopedMixin, Base):
    __tablename__ = "lesson_variant_sets"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", "revision"),)

    lesson_id: Mapped[str] = mapped_column(String(36))
    lesson_title: Mapped[str] = mapped_column(String(200))
    revision: Mapped[str] = mapped_column(String(64))
    source_markdown: Mapped[str] = mapped_column(Text)
    review_markdown: Mapped[str] = mapped_column(Text)
    reading_steps: Mapped[list[str]] = mapped_column(JSON)
