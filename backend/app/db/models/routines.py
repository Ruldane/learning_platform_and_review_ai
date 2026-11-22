from datetime import date
from typing import Any, Literal

from sqlalchemy import JSON, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

RoutineAction = Literal["due_reviews", "due_transfers", "missions_ending", "due_commitments"]
RoutineSource = Literal["manual", "scheduled"]


class Routine(UserScopedMixin, Base):
    __tablename__ = "routines"
    __table_args__ = (UniqueConstraint("user_id", "action"),)

    action: Mapped[RoutineAction] = mapped_column(String(64))
    local_time: Mapped[str] = mapped_column(String(5))
    enabled: Mapped[bool] = mapped_column(default=True)
    starts_on: Mapped[date] = mapped_column(Date)


class RoutineExecution(UserScopedMixin, Base):
    __tablename__ = "routine_executions"
    __table_args__ = (UniqueConstraint("user_id", "routine_id", "occurrence"),)

    routine_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("routines.id", ondelete="CASCADE")
    )
    occurrence: Mapped[str] = mapped_column(String(48))
    source: Mapped[RoutineSource] = mapped_column(String(12))
    result_count: Mapped[int]
    notices: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
