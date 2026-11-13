"""Lecture des leçons (SPEC 3.5, D91) : liste d'un programme (ordre des semaines puis des
modules), leçon complète avec ses ressources, PDF servi à son seul propriétaire."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.schemas import LessonOut, LessonSummaryOut
from app.features.lessons.service.production import MAX_ATTEMPTS
from app.features.lessons.service.resources import to_out
from app.features.lessons.service.status import read_with_open_sessions, shown
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


def _summary(lesson: Lesson, week_rank: int, open_ids: list[str]) -> dict[str, object]:
    status, reason = shown(lesson.status, lesson.session_id, lesson.failure_reason, open_ids)
    return {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "week_rank": week_rank,
        "title": lesson.title,
        "status": status,
        "failure_reason": reason,
        "attempts": min(lesson.attempts, MAX_ATTEMPTS),
        "word_count": lesson.word_count,
        "pdf_available": lesson.pdf_key is not None,
    }


def _states(rows: list[Lesson]) -> list[tuple[str, str | None]]:
    return [(row.status, row.session_id) for row in rows]


async def list_lessons(db: AsyncSession, user_id: str, program_id: str) -> list[LessonSummaryOut]:
    """Leçons d'un programme de l'utilisateur (404 `program_not_found` sinon), dans l'ordre du
    programme ; un module sans leçon encore créée n'apparaît pas. Une leçon interrompue hors
    du port apparaît en échec (`status`), sans écriture."""
    loaded = await load(db, user_id, program_id)
    ranks = _week_ranks(loaded)
    order = {module.id: index for index, module in enumerate(loaded.modules)}
    rows, open_ids = await read_with_open_sessions(
        db,
        user_id,
        program_id,
        lambda: LessonRepository(db, user_id).for_program(program_id),
        _states,
    )
    rows.sort(key=lambda lesson: order.get(lesson.module_id, len(order)))
    return [
        LessonSummaryOut.model_validate(_summary(row, ranks.get(row.module_id, 0), open_ids))
        for row in rows
    ]


async def _owned(db: AsyncSession, user_id: str, lesson_id: str) -> Lesson:
    lesson = await LessonRepository(db, user_id).get_fresh(lesson_id)
    if lesson is None:
        raise lesson_not_found()
    return lesson


async def get_lesson(db: AsyncSession, user_id: str, lesson_id: str) -> LessonOut:
    found = await _owned(db, user_id, lesson_id)  # son programme, puis relue après les sessions
    lesson, open_ids = await read_with_open_sessions(
        db,
        user_id,
        found.program_id,
        lambda: _owned(db, user_id, lesson_id),
        lambda x: _states([x]),
    )
    loaded = await load(db, user_id, lesson.program_id)
    resources = await ResourceRepository(db, user_id).for_module(lesson.module_id)
    return LessonOut.model_validate(
        {
            **_summary(lesson, _week_ranks(loaded).get(lesson.module_id, 0), open_ids),
            "program_id": lesson.program_id,
            "markdown": lesson.markdown,
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


async def ready_markdown(db: AsyncSession, user_id: str, module_id: str) -> str | None:
    """Le Markdown de la leçon prête du module, `None` si elle n'est pas prête (quiz, D101).
    Lecture pour les autres features (contrat 2)."""
    lesson = await LessonRepository(db, user_id).by_module(module_id)
    return lesson.markdown if lesson is not None and lesson.status == "ready" else None


async def ready_lesson_id(db: AsyncSession, user_id: str, module_id: str) -> str | None:
    """La leçon prête du module, `None` sinon (prochaine action de la carte, D107). Lecture
    pour les autres features (contrat 2)."""
    lesson = await LessonRepository(db, user_id).by_module(module_id)
    return lesson.id if lesson is not None and lesson.status == "ready" else None
