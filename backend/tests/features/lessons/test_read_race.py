"""Course de lecture du statut montré d'une leçon (re-relecture de 4.10, D97) : les sessions
ouvertes sont lues AVANT les leçons, donc une leçon finie entre les deux lectures n'apparaît
jamais en échec ; une session lancée entre les deux (leçon suivante) compte aussi comme ouverte,
par une seconde lecture faite seulement si une leçon paraît interrompue."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy import select

from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.service import status
from app.features.lessons.service.lessons import get_lesson, list_lessons
from app.features.program.repository import ModuleExtrasRepository
from app.features.program.service.programs import get_program
from app.features.program.service.runtime import ProgramRuntime
from tests.features.lessons.conftest import ME, RecordingLauncher, draft_program, validate
from tests.features.program.support import Factory

VIEWS = ("list", "lesson", "program")
# Lecture des lignes de leçon par chaque vue.
READS: dict[str, tuple[type, str]] = {
    "list": (LessonRepository, "for_program"),
    "lesson": (LessonRepository, "get_fresh"),
    "program": (ModuleExtrasRepository, "lessons"),
}


async def _first_lesson(factory: Factory, module_id: str) -> Lesson:
    async with factory() as db:
        return (await db.execute(select(Lesson).where(Lesson.module_id == module_id))).scalar_one()


async def _shown(factory: Factory, view: str, program_id: str, lesson: Lesson) -> str:
    async with factory() as db:
        if view == "list":
            listed = await list_lessons(db, ME, program_id)
            return next(x.status for x in listed if x.id == lesson.id)
        if view == "lesson":
            return (await get_lesson(db, ME, lesson.id)).status
        program = await get_program(db, ME, program_id)
        modules = {m.id: m.lesson_status for week in program.weeks for m in week.modules}
        return str(modules[lesson.module_id])


def _after_first_read(
    monkeypatch: pytest.MonkeyPatch, view: str, action: Callable[[], Awaitable[None]]
) -> None:
    """`action` juste après la première lecture des lignes de leçon de la vue."""
    owner, name = READS[view]
    real, done = getattr(owner, name), []

    async def read_then_act(self: Any, *args: Any) -> Any:
        rows = await real(self, *args)
        if not done:
            done.append(True)
            await action()
        return rows

    monkeypatch.setattr(owner, name, read_then_act)


@pytest.mark.parametrize("view", VIEWS)
async def test_lesson_finished_between_reads_is_never_shown_failed(
    view: str,
    monkeypatch: pytest.MonkeyPatch,
    program_rt: ProgramRuntime,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    lesson = await _first_lesson(db_session_factory, program.modules[0])
    assert lesson.status == "generating" and lesson.session_id is not None
    sid = lesson.session_id

    async def finish() -> None:  # publication (leçon prête), puis fin de la session
        async with db_session_factory() as db:
            row = await db.get(Lesson, lesson.id)
            assert row is not None
            row.status = "ready"
            await db.commit()
        await launcher.end(ME, sid)

    _after_first_read(monkeypatch, view, finish)
    assert await _shown(db_session_factory, view, program.program_id, lesson) != "failed"


@pytest.mark.parametrize("view", VIEWS)
async def test_session_launched_between_reads_counts_as_open(
    view: str,
    monkeypatch: pytest.MonkeyPatch,
    program_rt: ProgramRuntime,
    db_session_factory: Factory,
) -> None:
    """La première lecture des sessions précède le lancement ; la leçon est relue ensuite avec
    sa nouvelle session rangée : elle est en cours, pas en échec."""
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    lesson = await _first_lesson(db_session_factory, program.modules[0])
    real, calls = status.list_open_sessions, []

    async def not_yet_launched(*args: Any, **kwargs: Any) -> list[str]:
        calls.append(1)
        return [] if len(calls) == 1 else await real(*args, **kwargs)

    monkeypatch.setattr(status, "list_open_sessions", not_yet_launched)
    assert await _shown(db_session_factory, view, program.program_id, lesson) == "generating"
    assert len(calls) == 2
