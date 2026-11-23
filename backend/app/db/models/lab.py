from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class LabPreferencesRow(UserScopedMixin, Base):
    __tablename__ = "lab_preferences"
    __table_args__ = (UniqueConstraint("user_id"),)

    pinned: Mapped[list[str]] = mapped_column(JSON, default=list)
    tour: Mapped[str] = mapped_column(String(10), default="pending")
