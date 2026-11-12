from datetime import date
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
GoalStatus = Literal["council", "chosen", "planned"]
BoardKind = Literal["domain_map", "prerequisites", "timeline", "comparison"]


class Goal(UserScopedMixin, Base):
    """L'objectif de January et l'état de son conseil (SPEC 3.1, 13.3).

    `framing` porte le cadrage (questions et réponses) ; `minutes` le compte rendu du Scribe.
    `council_session_id` n'est pas une clé étrangère : l'objectif survit à sa session.
    """

    __tablename__ = "goals"

    text: Mapped[str] = mapped_column(Text)
    target_role: Mapped[str | None] = mapped_column(String(120), default=None)
    deadline: Mapped[date | None] = mapped_column(Date, default=None)
    weekly_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(String(16), default="council")
    framing: Mapped[dict[str, Any]] = mapped_column(default=dict)
    minutes: Mapped[str | None] = mapped_column(Text, default=None)
    council_session_id: Mapped[str | None] = mapped_column(String(36), default=None)


class Board(UserScopedMixin, Base):
    """Un état du tableau du Conseil : Mermaid du Scribe, ou scène retouchée par January.

    `scribe_key` (« session:step ») rend l'écriture du Scribe idempotente si un nœud est rejoué.
    """

    __tablename__ = "boards"
    # `uq_boards_user_id` : nom que la convention de `Base` donne à (user_id, scribe_key).
    __table_args__ = (UniqueConstraint("user_id", "scribe_key"),)

    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    step: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    mermaid: Mapped[str] = mapped_column(Text)
    scene: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    author: Mapped[str] = mapped_column(String(16), default="scribe")
    parent_id: Mapped[str | None] = mapped_column(String(36), default=None)
    scribe_key: Mapped[str | None] = mapped_column(String(80), default=None)


class Proposal(UserScopedMixin, Base):
    """Un parcours proposé par le Conseil ; `batch` numérote les tours de propositions."""

    __tablename__ = "proposals"
    # `uq_proposals_session_id` : (session_id, batch, rank) — un lot n'est écrit qu'une fois.
    __table_args__ = (
        UniqueConstraint("session_id", "batch", "rank"),
        Index("ix_proposals_user_goal", "user_id", "goal_id"),
    )

    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id", ondelete="CASCADE"))
    session_id: Mapped[str] = mapped_column(String(36))
    batch: Mapped[int] = mapped_column(Integer)
    rank: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120))
    promise: Mapped[str] = mapped_column(Text)
    duration_weeks: Mapped[int] = mapped_column(Integer)
    weekly_hours: Mapped[int] = mapped_column(Integer)
    skills: Mapped[list[Any]] = mapped_column(default=list)
    final_project: Mapped[str] = mapped_column(Text)
    tradeoffs: Mapped[list[Any]] = mapped_column(default=list)
    board_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("boards.id", ondelete="SET NULL"), default=None
    )
    chosen: Mapped[bool] = mapped_column(default=False)
