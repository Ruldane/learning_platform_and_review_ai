"""Production des leçons en chaîne (D91) : semaines 1 et 2 dès la validation, les suivantes
7 jours avant leur début, une seule chaîne par programme, 3 essais par leçon, session arrêtée
hors du port marquée en échec (Review Focus n° 5)."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.service import production
from app.features.lessons.service.production import INTERRUPTED, ensure_lessons
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.store import AgentLessonStore
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.validation import request_validation
from app.scheduler.base import JobContext
from app.scheduler.jobs import lessons_due
from tests.features.lessons.conftest import (
    ME,
    OTHER,
    RecordingLauncher,
    count_open_sessions,
    draft_program,
    validate,
)
from tests.features.program.support import MONDAY, Factory
from tests.support.program import full_week, plan

GRAPH = "lesson_factory"


async def lessons_of(factory: Factory, program_id: str) -> dict[str, Lesson]:
    async with factory() as db:
        rows = (await db.execute(select(Lesson).where(Lesson.program_id == program_id))).scalars()
        return {row.module_id: row for row in rows}


async def set_lesson(factory: Factory, module_id: str, **fields: object) -> None:
    async with factory() as db:
        lesson = (
            await db.execute(select(Lesson).where(Lesson.module_id == module_id))
        ).scalar_one()
        for key, value in fields.items():
            setattr(lesson, key, value)
        await db.commit()


async def test_validation_starts_lessons_for_weeks_one_and_two(
    program_rt: ProgramRuntime, launcher: RecordingLauncher, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    pid, first = program.program_id, program.modules[0]
    assert launcher.started == [(GRAPH, {"program_id": pid, "module_id": first})]
    lessons = await lessons_of(db_session_factory, pid)
    assert set(lessons) == set(program.modules)  # une leçon par module planifié
    assert (lessons[first].status, lessons[first].attempts) == ("generating", 1)
    assert lessons[first].session_id is not None
    assert lessons[program.modules[1]].status == "pending"


async def test_draft_program_starts_nothing(
    program_rt: ProgramRuntime, lessons_rt: LessonsRuntime, launcher: RecordingLauncher
) -> None:
    program = await draft_program(program_rt)
    assert await ensure_lessons(lessons_rt, ME, program.program_id) is None
    assert launcher.started == []


async def test_chain_runs_one_module_at_a_time(
    program_rt: ProgramRuntime, lessons_rt: LessonsRuntime, launcher: RecordingLauncher
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    assert await ensure_lessons(lessons_rt, ME, program.program_id) is None
    await validate(program_rt, program)  # rejoué : rien de plus
    assert len(launcher.started) == 1


async def test_next_module_excludes_current_session(
    program_rt: ProgramRuntime, store: AgentLessonStore, launcher: RecordingLauncher
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    pid = program.program_id
    async with program_rt.session_factory() as db:
        current = (await db.execute(select(Lesson.session_id))).scalars().first()
    assert current is not None
    await store.fail(ME, current, program.modules[0], "Contrôles non satisfaits")
    following = await store.next_module(ME, pid, exclude_session_id=current)
    assert following is not None and following != current
    assert launcher.started[-1] == (GRAPH, {"program_id": pid, "module_id": program.modules[1]})
    # Le nœud `next` rejoué après un arrêt : la chaîne existe déjà, rien de plus.
    assert await store.next_module(ME, pid, exclude_session_id=current) is None
    assert len(launcher.started) == 2


async def test_week_three_waits_until_seven_days_before(
    program_rt: ProgramRuntime,
    lessons_rt: LessonsRuntime,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    three = plan([full_week("Bases", [60]), full_week("Outils", [60]), full_week("Projet", [60])])
    program = await draft_program(program_rt, draft=three)
    await validate(program_rt, program)
    pid, (w1, w2, w3) = program.program_id, program.modules
    for module_id in (w1, w2):
        await set_lesson(db_session_factory, module_id, status="ready", attempts=1)
    for sid in await _open_ids(db_session_factory):
        await launcher.end(ME, sid)
    start = MONDAY  # semaine 3 : MONDAY + 14
    assert await ensure_lessons(lessons_rt, ME, pid, today=start + timedelta(days=6)) is None
    assert await ensure_lessons(lessons_rt, ME, pid, today=start + timedelta(days=7))
    assert launcher.started[-1] == (GRAPH, {"program_id": pid, "module_id": w3})


async def _open_ids(factory: Factory) -> list[str]:
    async with factory() as db:
        rows = (await db.execute(select(Lesson.session_id))).scalars().all()
    return [sid for sid in rows if sid]


async def test_failed_lesson_is_retried_at_most_three_times(
    program_rt: ProgramRuntime,
    lessons_rt: LessonsRuntime,
    store: AgentLessonStore,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    program = await draft_program(program_rt, draft=plan([full_week("Bases", [60])]))
    await validate(program_rt, program)
    pid, module_id = program.program_id, program.modules[0]
    for _ in range(5):
        lesson = (await lessons_of(db_session_factory, pid))[module_id]
        if lesson.status == "generating":
            assert lesson.session_id is not None
            await store.fail(ME, lesson.session_id, module_id, "Contrôles non satisfaits")
            await launcher.end(ME, lesson.session_id)
        await ensure_lessons(lessons_rt, ME, pid)
    lesson = (await lessons_of(db_session_factory, pid))[module_id]
    assert (lesson.status, lesson.attempts) == ("failed", 3)
    assert len(launcher.started) == 3
    assert await count_open_sessions(db_session_factory, GRAPH) == 0


async def test_session_stopped_outside_the_port_marks_the_lesson_failed(
    program_rt: ProgramRuntime,
    lessons_rt: LessonsRuntime,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    """Vérificateur invalide, quota, annulation : la session s'arrête sans `fail_lesson`."""
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    first, second = program.modules
    sid = (await lessons_of(db_session_factory, program.program_id))[first].session_id
    assert sid is not None
    await launcher.end(ME, sid, "failed")
    launched = await ensure_lessons(lessons_rt, ME, program.program_id)
    lessons = await lessons_of(db_session_factory, program.program_id)
    assert (lessons[first].status, lessons[first].failure_reason) == ("failed", INTERRUPTED)
    # Les modules jamais tentés passent d'abord ; le module en échec sera retenté ensuite.
    assert launched is not None and lessons[second].status == "generating"
    await launcher.end(ME, launched)
    await set_lesson(db_session_factory, second, status="ready")
    assert await ensure_lessons(lessons_rt, ME, program.program_id)
    assert launcher.started[-1][1]["module_id"] == first


async def test_launch_refused_restores_the_lesson(
    program_rt: ProgramRuntime,
    lessons_rt: LessonsRuntime,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    launcher.refuse = True
    program = await draft_program(program_rt)
    await validate(program_rt, program)  # la validation ne lève pas : la tâche rattrapera
    lesson = (await lessons_of(db_session_factory, program.program_id))[program.modules[0]]
    assert (lesson.status, lesson.attempts) == ("pending", 0)
    with pytest.raises(AppError) as caught:
        await ensure_lessons(lessons_rt, ME, program.program_id)
    assert caught.value.code == "engine_unavailable"
    launcher.refuse = False
    assert await ensure_lessons(lessons_rt, ME, program.program_id)


async def test_program_of_another_user_is_not_found(
    program_rt: ProgramRuntime, lessons_rt: LessonsRuntime, store: AgentLessonStore
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    with pytest.raises(AppError) as caught:
        await ensure_lessons(lessons_rt, OTHER, program.program_id)
    assert caught.value.code == "program_not_found"
    with pytest.raises(AppError):
        await store.next_module(OTHER, program.program_id, exclude_session_id="x")


async def test_scheduler_and_validation_start_one_chain(
    program_rt: ProgramRuntime,
    store: AgentLessonStore,
    job_ctx: JobContext,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review Focus n° 5 : validation, tâche « J-7 » et fin d'une leçon en même temps. La
    lecture des sessions ouvertes est ralentie : sans le verrou des leçons, chaque appel la
    passerait avant que le premier n'ait lancé sa session (quatre chaînes)."""
    real = production.list_open_sessions

    async def slow(*args: Any, **kwargs: Any) -> list[str]:
        found = await real(*args, **kwargs)
        await asyncio.sleep(0.02)
        return found

    monkeypatch.setattr(production, "list_open_sessions", slow)
    program = await draft_program(program_rt)
    launcher.refuse = True  # validé sans leçon lancée : tous les appels suivants sont en course
    await validate(program_rt, program)
    launcher.refuse = False
    await asyncio.gather(
        lessons_due.run(job_ctx),
        validate(program_rt, program),
        store.next_module(ME, program.program_id, exclude_session_id="session-finie"),
        lessons_due.run(job_ctx),
    )
    await lessons_due.run(job_ctx)
    assert await count_open_sessions(db_session_factory, GRAPH) == 1
    assert len(launcher.started) == 1
    lessons = await lessons_of(db_session_factory, program.program_id)
    assert sorted(lessons) == sorted(program.modules)  # jamais deux leçons pour un module
    assert [x.status for x in lessons.values()].count("generating") == 1


async def test_route_validation_starts_lessons_too(
    program_rt: ProgramRuntime, launcher: RecordingLauncher
) -> None:
    """« Valider » en ligne (brouillon sans session du Stratège ouverte) : même lancement ; un
    second clic (programme déjà validé) ne lance rien de plus."""
    program = await draft_program(program_rt)
    runtime = SimpleNamespace(runner=None)  # aucune session du Stratège à reprendre
    out = await request_validation(runtime, program_rt, ME, program.program_id)  # type: ignore[arg-type]
    assert out.status == "validated"
    assert [entry[1]["module_id"] for entry in launcher.started] == [program.modules[0]]
    await request_validation(runtime, program_rt, ME, program.program_id)  # type: ignore[arg-type]
    assert len(launcher.started) == 1
