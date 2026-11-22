from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class MeetingModule(UserScopedMixin, Base):
    __tablename__ = "meeting_modules"

    title: Mapped[str] = mapped_column(String(140))
    transcript: Mapped[str] = mapped_column(Text)
    source_digest: Mapped[str] = mapped_column(String(64))
    excerpts: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    selection: Mapped[list[int]] = mapped_column(JSON, default=list)
    module_steps: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
