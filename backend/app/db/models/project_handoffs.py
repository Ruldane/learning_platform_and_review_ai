from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class ProjectHandoff(UserScopedMixin, Base):
    __tablename__ = "project_handoffs"

    project_id: Mapped[str] = mapped_column(String(36))
    project_title: Mapped[str] = mapped_column(String(200))
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime)
    digest: Mapped[str] = mapped_column(String(64))
    markdown: Mapped[str] = mapped_column(Text)
