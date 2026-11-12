from datetime import date
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
SkillLevel = Literal["declare", "en_cours", "valide", "prouve"]
LEVEL_ORDER: tuple[SkillLevel, ...] = ("declare", "en_cours", "valide", "prouve")


class Skill(UserScopedMixin, Base):
    """Une compétence du graphe de January ; `norm_name` (`normalize_skill_name`) la dédoublonne."""

    __tablename__ = "skills"
    # `uq_skills_user_id` : (user_id, norm_name).
    __table_args__ = (UniqueConstraint("user_id", "norm_name"),)

    name: Mapped[str] = mapped_column(String(120))
    norm_name: Mapped[str] = mapped_column(String(120))
    domain: Mapped[str | None] = mapped_column(String(120), default=None)
    synonyms: Mapped[list[Any]] = mapped_column(default=list)


class SkillEdge(UserScopedMixin, Base):
    """`before` précède `after` : il faut connaître la première pour aborder la seconde."""

    __tablename__ = "skill_edges"
    # `uq_skill_edges_before_id` : (before_id, after_id).
    __table_args__ = (UniqueConstraint("before_id", "after_id"),)

    before_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    after_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))


class UserSkill(UserScopedMixin, Base):
    """Le niveau de January sur une compétence, avec ses preuves."""

    __tablename__ = "user_skills"
    # `uq_user_skills_user_id` : (user_id, skill_id).
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)

    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(16), default="declare")
    # Preuves : `core.skills.Evidence` (les chaînes de la phase 4 se lisent par `read_evidence`).
    evidence: Mapped[list[Any]] = mapped_column(default=list)
    # Échecs de fiches consécutifs sur cette compétence (`DEMOTE_AFTER` la fait redescendre).
    fail_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class SkillSnapshot(UserScopedMixin, Base):
    """Le relevé hebdomadaire des niveaux (courbe de la carte) : `skill_id → niveau`."""

    __tablename__ = "skill_snapshots"
    # `uq_skill_snapshots_user_id` : (user_id, week_start), le lundi de la semaine locale.
    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    week_start: Mapped[date] = mapped_column(Date)
    levels: Mapped[dict[str, Any]] = mapped_column(default=dict)
