"""Leçon dont la session s'arrête hors du port (correction 1 de la tâche 4.10, D91) : montrée en
échec dès la lecture, sans écriture ; chaîne reprise au passage suivant de la tâche planifiée,
3 essais au plus ; passage à vide en lecture seule (aucune écriture, aucun lancement)."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models.lessons import Lesson
from app.features.lessons.service.lessons import get_lesson, list_lessons
from app.features.lessons.service.production import ensure_lessons
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.status import INTERRUPTED
from app.features.program.service.programs import get_program
from app.features.program.service.runtime import ProgramRuntime
from app.scheduler.base import JobContext
from app.scheduler.jobs import lessons_due
from tests.features.lessons.conftest import (
    ME,
    RecordingLauncher,
    count_open_sessions,
    draft_program,
    validate,
)
from tests.features.program.support import Factory
from tests.support.program import full_week, plan

GRAPH = "lesson_factory"


async def _lesson(factory: Factory, module_id: str) -> Lesson:
    async with factory() as db:
        return (await db.execute(select(Lesson).where(Lesson.module_id == module_id))).scalar_one()


async def _shown(factory: Factory, program_id: str, module_id: str) -> tuple[str, str, str]:
    """Statut montré par la liste des leçons, la leçon et le programme."""
    async with factory() as db:
        listed = {x.module_id: x.status for x in await list_lessons(db, ME, program_id)}
        lesson = await get_lesson(db, ME, (await _lesson(factory, module_id)).id)
        program = await get_program(db, ME, program_id)
    modules = {m.id: m.lesson_status for week in program.weeks for m in week.modules}
    assert lesson.status != "failed" or lesson.failure_reason == INTERRUPTED
    return listed[module_id], lesson.status, str(modules[module_id])


async def test_read_shows_interrupted_lesson_failed_without_writing(
    program_rt: ProgramRuntime, launcher: RecordingLauncher, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    pid, first = program.program_id, program.modules[0]
    assert await _shown(db_session_factory, pid, first) == ("generating",) * 3  # session ouverte
    sid = (await _lesson(db_session_factory, first)).session_id
    assert sid is not None
    await launcher.end(ME, sid, "failed")  # quota, Vérificateur invalide… : hors du port
    assert await _shown(db_session_factory, pid, first) == ("failed",) * 3
    row = await _lesson(db_session_factory, first)
    assert (row.status, row.failure_reason) == ("generating", None)  # rien d'écrit


async def test_lesson_being_launched_still_shows_generating(
    program_rt: ProgramRuntime, launcher: RecordingLauncher, db_session_factory: Factory
) -> None:
    """Entre la décision et le lancement, la session n'est pas encore rangée : en cours."""
    launcher.refuse = True
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    first = program.modules[0]
    async with db_session_factory() as db:
        row = (await db.execute(select(Lesson).where(Lesson.module_id == first))).scalar_one()
        row.status = "generating"
        await db.commit()
    assert await _shown(db_session_factory, program.program_id, first) == ("generating",) * 3


async def test_chain_resumes_at_next_pass_three_attempts_at_most(
    program_rt: ProgramRuntime,
    job_ctx: JobContext,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    """Chaque session s'arrête hors du port : le passage suivant de la tâche relance la leçon,
    jusqu'à 3 essais ; ensuite plus rien n'est lancé."""
    program = await draft_program(program_rt, draft=plan([full_week("Bases", [60])]))
    await validate(program_rt, program)
    module_id = program.modules[0]
    for _ in range(5):
        row = await _lesson(db_session_factory, module_id)
        if row.status == "generating" and row.session_id is not None:
            await launcher.end(ME, row.session_id, "failed")
        await lessons_due.run(job_ctx)
    row = await _lesson(db_session_factory, module_id)
    assert (row.status, row.attempts, row.failure_reason) == ("failed", 3, INTERRUPTED)
    assert len(launcher.started) == 3
    assert await count_open_sessions(db_session_factory, GRAPH) == 0


@contextmanager
def _writes(engine: AsyncEngine) -> Iterator[list[str]]:
    """Requêtes d'écriture émises sur la base pendant le bloc."""
    seen: list[str] = []

    def record(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        if statement.lstrip().split(" ", 1)[0].upper() in ("INSERT", "UPDATE", "DELETE"):
            seen.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        yield seen
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)


async def test_idle_pass_only_reads(
    program_rt: ProgramRuntime,
    lessons_rt: LessonsRuntime,
    job_ctx: JobContext,
    launcher: RecordingLauncher,
    db_engine: AsyncEngine,
    db_session_factory: Factory,
) -> None:
    """Chaîne en cours, puis tout prêt : un passage ne fait que lire (ni écriture, ni
    lancement, donc aucun appel au modèle)."""
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    with _writes(db_engine) as writes:
        await lessons_due.run(job_ctx)  # une chaîne tourne déjà
    assert writes == [] and len(launcher.started) == 1
    sid = (await _lesson(db_session_factory, program.modules[0])).session_id
    assert sid is not None
    await launcher.end(ME, sid)
    async with db_session_factory() as db:
        for row in (await db.execute(select(Lesson))).scalars():
            row.status = "ready"
        await db.commit()
    with _writes(db_engine) as writes:
        assert await ensure_lessons(lessons_rt, ME, program.program_id) is None  # rien de dû
    assert writes == [] and len(launcher.started) == 1
