"""Un module « Valider mes acquis » (D220) n'a jamais de leçon : la production n'en crée pas,
n'en lance pas, et une écriture directe est refusée (D309)."""

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.schemas import LessonWriteIn
from app.features.lessons.service.direct import write_lesson
from app.features.lessons.service.production import ensure_lessons
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.validation_module import add_validation_module
from tests.features.lessons.conftest import ME, RecordingLauncher, draft_program, validate
from tests.features.program.support import MONDAY, Factory


async def _lesson_modules(factory: Factory, program_id: str) -> set[str]:
    async with factory() as db:
        rows = await db.execute(select(Lesson.module_id).where(Lesson.program_id == program_id))
        return set(rows.scalars())


async def test_validation_module_gets_no_lesson(
    program_rt: ProgramRuntime,
    lessons_rt: LessonsRuntime,
    launcher: RecordingLauncher,
    db_session_factory: Factory,
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    module_id = await add_validation_module(program_rt, ME, program.program_id, ["English"], MONDAY)
    await ensure_lessons(lessons_rt, ME, program.program_id)
    assert module_id not in await _lesson_modules(db_session_factory, program.program_id)
    assert all(args["module_id"] != module_id for _, args in launcher.started)


async def test_direct_write_on_validation_module_is_refused(
    program_rt: ProgramRuntime, lessons_rt: LessonsRuntime
) -> None:
    program = await draft_program(program_rt)
    await validate(program_rt, program)
    module_id = await add_validation_module(program_rt, ME, program.program_id, ["English"], MONDAY)
    with pytest.raises(AppError) as caught:
        await write_lesson(
            lessons_rt, ME, module_id, LessonWriteIn(markdown="x" * 300), is_mcp=True
        )
    assert caught.value.code == "module_without_lesson"
