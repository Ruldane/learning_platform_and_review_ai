"""Lecture des leçons (SPEC 3.5, D91) : liste d'un programme (ordre des semaines puis des
modules), leçon complète avec ses ressources, PDF servi à son seul propriétaire."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.schemas import LessonOut, LessonSummaryOut
from app.features.lessons.service.resources import to_out
from app.features.program.service.programs import Loaded, load
from app.providers.storage.base import FileStorage, StorageKeyInvalid


def lesson_not_found() -> AppError:
    return AppError("lesson_not_found", "Leçon introuvable.", 404)


def lesson_pdf_missing() -> AppError:
    return AppError("lesson_pdf_missing", "Le PDF de cette leçon n'est pas encore disponible.", 404)


def _week_ranks(loaded: Loaded) -> dict[str, int]:
    """`module → rang de sa semaine`."""
    weeks = {week.id: week.rank for week in loaded.weeks}
    return {module.id: weeks.get(module.week_id, 0) for module in loaded.modules}


def _summary(lesson: Lesson, week_rank: int) -> dict[str, object]:
    return {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "week_rank": week_rank,
        "title": lesson.title,
        "status": lesson.status,
        "word_count": lesson.word_count,
        "pdf_available": lesson.pdf_key is not None,
    }


async def list_lessons(db: AsyncSession, user_id: str, program_id: str) -> list[LessonSummaryOut]:
    """Leçons d'un programme de l'utilisateur (404 `program_not_found` sinon), dans l'ordre du
    programme ; un module sans leçon encore créée n'apparaît pas."""
    loaded = await load(db, user_id, program_id)
    ranks = _week_ranks(loaded)
    order = {module.id: index for index, module in enumerate(loaded.modules)}
    rows = await LessonRepository(db, user_id).for_program(program_id)
    rows.sort(key=lambda lesson: order.get(lesson.module_id, len(order)))
    return [
        LessonSummaryOut.model_validate(_summary(row, ranks.get(row.module_id, 0))) for row in rows
    ]


async def _owned(db: AsyncSession, user_id: str, lesson_id: str) -> Lesson:
    lesson = await LessonRepository(db, user_id).get_fresh(lesson_id)
    if lesson is None:
        raise lesson_not_found()
    return lesson


async def get_lesson(db: AsyncSession, user_id: str, lesson_id: str) -> LessonOut:
    lesson = await _owned(db, user_id, lesson_id)
    loaded = await load(db, user_id, lesson.program_id)
    resources = await ResourceRepository(db, user_id).for_module(lesson.module_id)
    return LessonOut.model_validate(
        {
            **_summary(lesson, _week_ranks(loaded).get(lesson.module_id, 0)),
            "program_id": lesson.program_id,
            "markdown": lesson.markdown,
            "failure_reason": lesson.failure_reason,
            "resources": [to_out(row) for row in resources],
        }
    )


async def lesson_pdf(
    db: AsyncSession, storage: FileStorage, user_id: str, lesson_id: str
) -> tuple[str, bytes]:
    """Titre et PDF de la leçon de l'utilisateur ; 404 `lesson_pdf_missing` tant qu'absent."""
    lesson = await _owned(db, user_id, lesson_id)
    if lesson.pdf_key is None:
        raise lesson_pdf_missing()
    try:
        return lesson.title, await storage.read(user_id, lesson.pdf_key)
    except (FileNotFoundError, StorageKeyInvalid):
        raise lesson_pdf_missing() from None
