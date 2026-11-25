"""Watch sources and articles collected in the reading stack."""

from datetime import datetime
from typing import Literal

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

type SourceKind = Literal["topic", "site", "rss"]
type ReadingKind = Literal["offer", "article", "paper", "release"]


class ReadingSource(UserScopedMixin, Base):
    __tablename__ = "reading_sources"
    __table_args__ = (UniqueConstraint("user_id", "kind", "value"),)

    kind: Mapped[SourceKind] = mapped_column(String(12))
    label: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(String(2000))
    active: Mapped[bool] = mapped_column(default=True)


class ReadingItem(UserScopedMixin, Base):
    __tablename__ = "reading_items"
    __table_args__ = (UniqueConstraint("user_id", "url"),)

    kind: Mapped[ReadingKind] = mapped_column(String(12))
    url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(String(600))
    text: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(240))
    company: Mapped[str | None] = mapped_column(String(160))
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
