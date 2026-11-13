"""Faits d'une semaine pour le bilan (D106) : temps prévu, fait et en retard, avance prise, quiz
notés, temps d'étude et captures, comptés sur la semaine locale de January (Paris : le dimanche
23:30 compte, le lundi 00:30 non) ; le programme d'un autre est introuvable."""

from datetime import UTC, date, datetime

import pytest

from app.core.errors import AppError
from app.db.models.study import JournalEntry, Quiz, QuizAttempt, StudySession
from app.features.program.schemas import TaskPatch
from app.features.program.service.editing import move_or_edit_task
from app.features.program.service.runtime import ProgramRuntime
from app.features.replan.service.facts import week_facts
from app.features.replan.service.review import classify, late_ratio
from tests.features.program.support import MONDAY, WEEK1_LOAD, Factory
from tests.features.replan.conftest import ME, OTHER, tasks_of, validated

INSIDE = datetime(2026, 11, 22, 22, 30, tzinfo=UTC)  # dimanche 23:30 à Paris : semaine 1
OUTSIDE = datetime(2026, 11, 22, 23, 30, tzinfo=UTC)  # lundi 00:30 à Paris : semaine 2


async def _activity(factory: Factory, program_id: str, module_id: str) -> None:
    async with factory() as db:
        quiz = Quiz(user_id=ME, module_id=module_id, program_id=program_id, title="Quiz 1")
        db.add(quiz)
        await db.flush()
        for score, at in ((80, INSIDE), (40, OUTSIDE)):
            db.add(
                QuizAttempt(user_id=ME, quiz_id=quiz.id, status="graded", score=score, graded_at=at)
            )
        for minutes, at in ((50, INSIDE), (25, OUTSIDE)):
            db.add(
                StudySession(
                    user_id=ME, lesson_id="l", module_id=module_id, program_id=program_id,
                    mode="guided", status="finished", minutes=minutes, ended_at=at,
                )
            )  # fmt: skip
        for day in (date(2026, 11, 22), date(2026, 11, 23)):
            db.add(JournalEntry(user_id=ME, kind="capture", text="Note", occurred_on=day))
        await db.commit()


async def test_week_facts_count_local_week(program_rt: ProgramRuntime) -> None:
    program_id = await validated(program_rt)
    tasks = await tasks_of(program_rt.session_factory, program_id)
    first = [t for t in tasks if t.planned_date < date(2026, 11, 23)]
    ahead = next(t for t in tasks if t.planned_date >= date(2026, 11, 23))
    for task in (first[0], ahead):
        await move_or_edit_task(program_rt, ME, task.id, TaskPatch(status="done"))
    await _activity(program_rt.session_factory, program_id, first[0].module_id)
    async with program_rt.session_factory() as db:
        facts = await week_facts(db, ME, program_id, MONDAY)
    assert (facts.planned_minutes, facts.done_minutes) == (WEEK1_LOAD, first[0].minutes)
    assert facts.late_minutes == WEEK1_LOAD - first[0].minutes
    assert (facts.tasks_planned, facts.tasks_done, facts.done_ahead) == (len(first), 1, 1)
    assert facts.quiz_scores == [80] and facts.study_minutes == 50 and facts.captures == 1
    assert late_ratio(facts) > 0.3 and classify(facts, 0.5) == "late_twice"
    assert classify(facts, None) == "late"


async def test_week_facts_other_user_program_is_not_found(program_rt: ProgramRuntime) -> None:
    theirs = await validated(program_rt, OTHER)
    async with program_rt.session_factory() as db:
        with pytest.raises(AppError) as exc:
            await week_facts(db, ME, theirs, MONDAY)
    assert exc.value.code == "program_not_found"
