"""Modèles de l'étude (5.2) : défauts, unicités, index partiels et cascades."""

from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.learning import Goal
from app.db.models.program import Module, PlanVersion, Program, Week
from app.db.models.skills import SkillSnapshot
from app.db.models.study import (
    Flashcard,
    JournalEntry,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    StudySession,
)

DAY = date(2026, 11, 12)


async def _module(db: AsyncSession) -> Module:
    goal = Goal(user_id="u1", text="x")
    db.add(goal)
    await db.flush()
    program = Program(
        user_id="u1",
        goal_id=goal.id,
        title="P",
        start_date=DAY,
        weekly_minutes=840,
        cap_minutes=714,
    )
    db.add(program)
    await db.flush()
    week = Week(
        user_id="u1", program_id=program.id, rank=1, theme="t", objective="o", deliverable="d",
        start_date=DAY,
    )  # fmt: skip
    db.add(week)
    await db.flush()
    module = Module(user_id="u1", week_id=week.id, program_id=program.id, rank=1, title="Python")
    db.add(module)
    await db.flush()
    return module


def _study(user_id: str, status: str = "open") -> StudySession:
    return StudySession(
        user_id=user_id,
        lesson_id="l1",
        module_id="m1",
        program_id="p1",
        mode="socratic",
        status=status,
    )


async def test_second_open_study_session_violates_unique_index(db_session: AsyncSession) -> None:
    db_session.add(_study("u1"))
    db_session.add(_study("u2"))  # un autre utilisateur n'est pas gêné
    db_session.add(_study("u1", "finished"))
    db_session.add(_study("u1", "cancelled"))
    await db_session.flush()
    db_session.add(_study("u1"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_study_session_defaults(db_session: AsyncSession) -> None:
    row = StudySession(user_id="u1", lesson_id="l1", module_id="m1", program_id="p1", mode="direct")
    db_session.add(row)
    await db_session.flush()
    assert (row.status, row.minutes, row.task_ids) == ("open", 0, [])
    assert row.worked_minutes is None and row.ended_at is None and row.outcome is None


def _attempt(quiz_id: str, status: str = "grading", user_id: str = "u1") -> QuizAttempt:
    return QuizAttempt(user_id=user_id, quiz_id=quiz_id, answers=[], status=status)


async def test_second_grading_attempt_violates_unique_index(db_session: AsyncSession) -> None:
    _, quiz = await _quiz(db_session)
    db_session.add(_attempt(quiz.id, "graded"))
    db_session.add(_attempt(quiz.id, "failed"))
    db_session.add(_attempt(quiz.id, "grading", user_id="u2"))
    db_session.add(_attempt(quiz.id))
    await db_session.flush()
    db_session.add(_attempt(quiz.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def _quiz(db: AsyncSession) -> tuple[Module, Quiz]:
    module = await _module(db)
    quiz = Quiz(user_id="u1", module_id=module.id, program_id=module.program_id, title="Quiz")
    db.add(quiz)
    await db.flush()
    return module, quiz


async def test_quiz_tree_defaults(db_session: AsyncSession) -> None:
    module, quiz = await _quiz(db_session)
    assert quiz.status == "generating" and quiz.session_id is None
    question = QuizQuestion(
        user_id="u1", quiz_id=quiz.id, rank=1, type="qcm", prompt="2 + 2 ?", skill="Calcul"
    )
    attempt = _attempt(quiz.id)
    db_session.add_all([question, attempt])
    await db_session.flush()
    assert (question.choices, question.rubric, question.correct_index) == ([], [], None)
    assert (attempt.status, attempt.score, attempt.results) == ("grading", None, None)
    db_session.add(Quiz(user_id="u1", module_id=module.id, program_id="p", title="Doublon"))
    with pytest.raises(IntegrityError):  # un quiz par module
        await db_session.flush()


async def test_module_delete_cascades_to_quiz(db_session: AsyncSession) -> None:
    module, quiz = await _quiz(db_session)
    db_session.add_all(
        [
            QuizQuestion(
                user_id="u1", quiz_id=quiz.id, rank=1, type="short", prompt="p", skill="s"
            ),
            _attempt(quiz.id),
        ]
    )
    await db_session.flush()
    await db_session.execute(delete(Module).where(Module.id == module.id))
    await db_session.flush()
    for model in (Quiz, QuizQuestion, QuizAttempt):
        assert (await db_session.execute(select(model))).first() is None, model.__name__


async def test_question_rank_is_unique_per_quiz(db_session: AsyncSession) -> None:
    _, quiz = await _quiz(db_session)
    for _ in range(2):
        db_session.add(
            QuizQuestion(user_id="u1", quiz_id=quiz.id, rank=1, type="qcm", prompt="p", skill="s")
        )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_flashcard_front_is_unique_per_user(db_session: AsyncSession) -> None:
    def card(user_id: str) -> Flashcard:
        return Flashcard(
            user_id=user_id, front="Q ?", back="R", front_hash="h", source="lesson", due_date=DAY
        )

    first = card("u1")
    db_session.add_all([first, card("u2")])
    await db_session.flush()
    assert first.step == 0 and first.last_reviewed_on is None
    db_session.add(card("u1"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_journal_ref_key_is_unique_per_user_but_null_repeats(
    db_session: AsyncSession,
) -> None:
    def entry(user_id: str, ref_key: str | None) -> JournalEntry:
        return JournalEntry(
            user_id=user_id, kind="capture", text="t", occurred_on=DAY, ref_key=ref_key
        )

    db_session.add_all([entry("u1", None), entry("u1", None), entry("u1", "k"), entry("u2", "k")])
    await db_session.flush()
    db_session.add(entry("u1", "k"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_new_columns_defaults(db_session: AsyncSession) -> None:
    module = await _module(db_session)
    version = PlanVersion(user_id="u1", program_id=module.program_id, version=1, snapshot={})
    db_session.add(version)
    await db_session.flush()
    assert (version.kind, version.status) == ("build", "pending")
    assert (version.base_fingerprint, version.review_entry_id, version.week_loads) == (
        None,
        None,
        None,
    )


async def test_skill_snapshot_is_unique_per_user_and_week(db_session: AsyncSession) -> None:
    def snapshot(user_id: str) -> SkillSnapshot:
        return SkillSnapshot(user_id=user_id, week_start=date(2026, 11, 9), levels={"s1": "valide"})

    first = snapshot("u1")
    db_session.add_all([first, snapshot("u2")])
    await db_session.flush()
    assert first.levels == {"s1": "valide"}
    db_session.add(snapshot("u1"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
