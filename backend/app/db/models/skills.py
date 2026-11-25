from datetime import date
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

# Types shared with `app.agents`, which cannot import a feature (contract 6).
SkillLevel = Literal["declared", "in_progress", "validated", "proven"]
LEVEL_ORDER: tuple[SkillLevel, ...] = ("declared", "in_progress", "validated", "proven")


class Skill(UserScopedMixin, Base):
    """A skill of January's graph; `norm_name` (`normalize_skill_name`) de-duplicates it."""

    __tablename__ = "skills"
    # `uq_skills_user_id` : (user_id, norm_name).
    __table_args__ = (UniqueConstraint("user_id", "norm_name"),)

    name: Mapped[str] = mapped_column(String(120))
    norm_name: Mapped[str] = mapped_column(String(120))
    domain: Mapped[str | None] = mapped_column(String(120), default=None)
    synonyms: Mapped[list[Any]] = mapped_column(default=list)


class SkillEdge(UserScopedMixin, Base):
    """`before` comes before `after`: the first must be known before tackling the second."""

    __tablename__ = "skill_edges"
    # `uq_skill_edges_before_id` : (before_id, after_id).
    __table_args__ = (UniqueConstraint("before_id", "after_id"),)

    before_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    after_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))


class UserSkill(UserScopedMixin, Base):
    """January's level on a skill, with its evidence."""

    __tablename__ = "user_skills"
    # `uq_user_skills_user_id` : (user_id, skill_id).
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)

    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(16), default="declared")
    # Evidence: `core.skills.Evidence` (the phase 4 chains are read through `read_evidence`).
    evidence: Mapped[list[Any]] = mapped_column(default=list)
    # Consecutive failed cards on this skill (`DEMOTE_AFTER` brings it back down).
    fail_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class SkillSnapshot(UserScopedMixin, Base):
    """The weekly record of levels (the map's curve): `skill_id → level`."""

    __tablename__ = "skill_snapshots"
    # `uq_skill_snapshots_user_id`: (user_id, week_start), the Monday of the local week.
    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    week_start: Mapped[date] = mapped_column(Date)
    levels: Mapped[dict[str, Any]] = mapped_column(default=dict)
