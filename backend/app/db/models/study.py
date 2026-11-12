"""Tables de l'étude (phase 5, D99) : quiz, fiches de révision, sessions guidées, journal."""

from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
QuizStatus = Literal["generating", "ready", "failed"]
QuestionType = Literal["qcm", "short", "code", "explain"]
AttemptStatus = Literal["grading", "graded", "failed"]
StudyMode = Literal["socratic", "feynman", "direct"]
StudyStatus = Literal["open", "finished", "cancelled"]
JournalKind = Literal["capture", "study_session", "quiz", "weekly_review"]
CardSource = Literal["lesson", "quiz", "study", "capture"]


class Quiz(UserScopedMixin, Base):
    """Le quiz d'un module (un seul) ; l'Examinateur l'écrit, `status` dit où il en est."""

    __tablename__ = "quizzes"
    # `uq_quizzes_module_id` : un quiz par module.
    __table_args__ = (UniqueConstraint("module_id"),)

    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("modules.id", ondelete="CASCADE"))
    program_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="generating")
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)


class QuizQuestion(UserScopedMixin, Base):
    """Une question ; `correct_index` ne sert qu'au QCM, `expected` et `rubric` aux ouvertes."""

    __tablename__ = "quiz_questions"
    # `uq_quiz_questions_quiz_id` : (quiz_id, rank).
    __table_args__ = (UniqueConstraint("quiz_id", "rank"),)

    quiz_id: Mapped[str] = mapped_column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(8))
    prompt: Mapped[str] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text, default=None)
    choices: Mapped[list[Any]] = mapped_column(default=list)
    correct_index: Mapped[int | None] = mapped_column(Integer, default=None)
    expected: Mapped[str] = mapped_column(Text, default="")
    rubric: Mapped[list[Any]] = mapped_column(default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    skill: Mapped[str] = mapped_column(String(120))


class QuizAttempt(UserScopedMixin, Base):
    """Une tentative de January. Au plus une est en cours de notation par quiz (D99, F3)."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_user_quiz", "user_id", "quiz_id"),
        Index(
            "uq_quiz_attempts_grading",
            "user_id",
            "quiz_id",
            unique=True,
            sqlite_where=text("status = 'grading'"),
        ),
    )

    quiz_id: Mapped[str] = mapped_column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"))
    answers: Mapped[list[Any]] = mapped_column(default=list)
    status: Mapped[str] = mapped_column(String(8), default="grading")
    score: Mapped[int | None] = mapped_column(Integer, default=None)
    results: Mapped[list[Any] | None] = mapped_column(default=None)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    graded_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    retry_on: Mapped[date | None] = mapped_column(Date, default=None)
    followup: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class Flashcard(UserScopedMixin, Base):
    """Une fiche de révision espacée ; `step` indexe `INTERVALS`, `due_date` est un jour local."""

    __tablename__ = "flashcards"
    # `uq_flashcards_user_id` : (user_id, front_hash) ; `ix_flashcards_user_due` : la file du jour.
    __table_args__ = (
        UniqueConstraint("user_id", "front_hash"),
        Index("ix_flashcards_user_due", "user_id", "due_date"),
    )

    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    front_hash: Mapped[str] = mapped_column(String(64))
    skill: Mapped[str | None] = mapped_column(String(120), default=None)
    module_id: Mapped[str | None] = mapped_column(String(36), default=None)
    source: Mapped[str] = mapped_column(String(8))
    source_id: Mapped[str | None] = mapped_column(String(36), default=None)
    step: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[date] = mapped_column(Date)
    last_reviewed_on: Mapped[date | None] = mapped_column(Date, default=None)


class StudySession(UserScopedMixin, Base):
    """Un bloc d'étude guidé par le Tuteur. Une seule session `open` par utilisateur (index
    unique partiel) : un second « Commencer mon bloc » retombe sur elle."""

    __tablename__ = "study_sessions"
    __table_args__ = (
        Index(
            "uq_study_sessions_open", "user_id", unique=True, sqlite_where=text("status = 'open'")
        ),
    )

    lesson_id: Mapped[str] = mapped_column(String(36))
    module_id: Mapped[str] = mapped_column(String(36))
    program_id: Mapped[str] = mapped_column(String(36))
    mode: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="open")
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    question: Mapped[str | None] = mapped_column(Text, default=None)
    task_ids: Mapped[list[Any]] = mapped_column(default=list)  # bloc retenu au départ
    worked_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class JournalEntry(UserScopedMixin, Base):
    """Une ligne du journal chronologique (captures, sessions, quiz, bilans). Seul
    `capture.service.journal.add_entry` l'écrit ; `ref_key` la rend idempotente."""

    __tablename__ = "journal_entries"
    # `uq_journal_entries_user_id` : (user_id, ref_key) ; plusieurs `ref_key` NULL permis.
    __table_args__ = (
        UniqueConstraint("user_id", "ref_key"),
        Index("ix_journal_entries_user_created", "user_id", "created_at"),
    )

    kind: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    occurred_on: Mapped[date] = mapped_column(Date)
    ref_key: Mapped[str | None] = mapped_column(String(120), default=None)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    study_session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    quiz_attempt_id: Mapped[str | None] = mapped_column(String(36), default=None)
    memory_item_id: Mapped[str | None] = mapped_column(String(36), default=None)
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
