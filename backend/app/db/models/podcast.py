from datetime import date
from typing import Any, Literal

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

type EpisodeStatus = Literal["queued", "script", "ready", "transcript", "failed"]


class PodcastEpisode(UserScopedMixin, Base):
    __tablename__ = "podcast_episodes"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    day: Mapped[date] = mapped_column(Date)
    lesson_id: Mapped[str] = mapped_column(String(36))
    module_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[EpisodeStatus] = mapped_column(String(12), default="queued")
    script: Mapped[dict[str, Any] | None]
    session_id: Mapped[str | None] = mapped_column(String(36))
    audio_key: Mapped[str | None] = mapped_column(String(180))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
