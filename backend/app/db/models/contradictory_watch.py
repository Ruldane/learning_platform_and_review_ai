from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class WatchExperiment(UserScopedMixin, Base):
    __tablename__ = "watch_experiments"

    title: Mapped[str] = mapped_column(String(140))
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    protocol: Mapped[str] = mapped_column(Text)
    criterion: Mapped[str] = mapped_column(Text)
    observation: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    completed: Mapped[bool] = mapped_column(default=False)
