"""Reading lessons (SPEC 3.5, D91): a program's list (week order, then module order), full
lesson with its resources, PDF served to its owner only."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.db.models.program import Task
from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.schemas import LessonOut, LessonSummaryOut
from app.features.lessons.service.production import MAX_ATTEMPTS
from app.features.lessons.service.resources import to_out
from app.features.lessons.service.status import (
    VERIFICATION_INTERRUPTED,
    read_with_open_sessions,
    shown,
)
from app.features.program.service.programs import Loaded, load
from app.providers.storage.base import FileStorage, StorageKeyInvalid


def lesson_not_found() -> AppError:
    return AppError("lesson_not_found", "Lesson not found.", 404)


def lesson_pdf_missing() -> AppError:
    return AppError("lesson_pdf_missing", "This lesson's PDF is not available yet.", 404)


def _week_ranks(loaded: Loaded) -> dict[str, int]:
    """`module → rank of its week`."""
    weeks = {week.id: week.rank for week in loaded.weeks}
    return {module.id: weeks.get(module.week_id, 0) for module in loaded.modules}


def _summary(
    lesson: Lesson, week_rank: int, open_ids: list[str], tasks: list[Task]
) -> dict[str, object]:
    """Summary of a lesson; `tasks`: those of its module (completed when all are done)."""
    status, reason = shown(lesson.status, lesson.session_id, lesson.failure_reason, open_ids)
    sid = lesson.verification_session_id
    verification_reason = lesson.verification_failure_reason
    if sid is not None and sid not in open_ids:
        sid, verification_reason = None, VERIFICATION_INTERRUPTED
        if lesson.status == "generating":
            status, reason = "failed", verification_reason
    done = sum(1 for task in tasks if task.status == "done")
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
        "done_tasks": done,
        "total_tasks": len(tasks),
        "completed": bool(tasks) and done == len(tasks),
        "verification_session_id": sid,
        "verification_failure_reason": verification_reason,
    }


def _states(rows: list[Lesson]) -> list[tuple[str, str | None]]:
    return [
        ("generating", row.verification_session_id)
        if row.verification_session_id
        else (row.status, row.session_id)
        for row in rows
    ]


async def list_lessons(db: AsyncSession, user_id: str, program_id: str) -> list[LessonSummaryOut]:
    """Lessons of one of the user's programs (404 `program_not_found` otherwise), in program
    order; a module with no lesson created yet does not appear. A lesson interrupted outside the
    port appears as failed (`status`), without any write."""
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
        LessonSummaryOut.model_validate(
            _summary(
                row, ranks.get(row.module_id, 0), open_ids, loaded.tasks_of_module(row.module_id)
            )
        )
        for row in rows
    ]


async def _owned(db: AsyncSession, user_id: str, lesson_id: str) -> Lesson:
    lesson = await LessonRepository(db, user_id).get_fresh(lesson_id)
    if lesson is None:
        raise lesson_not_found()
    return lesson


async def get_lesson(db: AsyncSession, user_id: str, lesson_id: str) -> LessonOut:
    found = await _owned(db, user_id, lesson_id)  # its program, then read again after the sessions
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
            **_summary(
                lesson,
                _week_ranks(loaded).get(lesson.module_id, 0),
                open_ids,
                loaded.tasks_of_module(lesson.module_id),
            ),
            "program_id": lesson.program_id,
            "markdown": lesson.markdown,
            "resources": [to_out(row) for row in resources],
            "verification_feedback": lesson.verification_feedback or [],
        }
    )


async def lesson_pdf(
    db: AsyncSession, storage: FileStorage, user_id: str, lesson_id: str
) -> tuple[str, bytes]:
    """Title and PDF of the user's lesson; 404 `lesson_pdf_missing` while missing."""
    lesson = await _owned(db, user_id, lesson_id)
    if lesson.pdf_key is None:
        raise lesson_pdf_missing()
    try:
        return lesson.title, await storage.read(user_id, lesson.pdf_key)
    except (FileNotFoundError, StorageKeyInvalid):
        raise lesson_pdf_missing() from None


async def ready_markdown(db: AsyncSession, user_id: str, module_id: str) -> str | None:
    """Markdown of the module's ready lesson, `None` if it is not ready (quiz, D101).
    Read for other features (contract 2)."""
    lesson = await LessonRepository(db, user_id).by_module(module_id)
    return lesson.markdown if lesson is not None and lesson.status == "ready" else None


@dataclass(frozen=True)
class PublishedChapter:
    id: str
    module_id: str
    title: str
    markdown: str
    published_at: datetime


async def published_chapters(
    db: AsyncSession, user_id: str, program_id: str
) -> tuple[PublishedChapter, ...]:
    """Published versions only, even while a new edit is being prepared."""
    rows = await LessonRepository(db, user_id).for_program(program_id)
    return tuple(
        PublishedChapter(row.id, row.module_id, row.title, row.markdown, row.updated_at)
        for row in rows
        if row.status == "ready" and row.markdown.strip()
    )


async def ready_lesson_id(db: AsyncSession, user_id: str, module_id: str) -> str | None:
    """The module's ready lesson, `None` otherwise (the card's next action, D107). Read for
    other features (contract 2)."""
    lesson = await LessonRepository(db, user_id).by_module(module_id)
    return lesson.id if lesson is not None and lesson.status == "ready" else None


async def published_lesson_routes(db: AsyncSession, user_id: str) -> dict[str, str]:
    """Published chapter ids by module, without reading the content."""
    return await LessonRepository(db, user_id).ready_routes()


@dataclass(frozen=True)
class RecentLesson:
    id: str
    title: str
    status: Literal["ready", "failed"]
    at: datetime


async def recent_lessons(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[RecentLesson]:
    """Lessons that became ready or failed within `[after, before]`, most recent first
    (activity feed, 8.7). Read for other features (contract 2): the stored state, without
    re-reading the sessions."""
    rows = await LessonRepository(db, user_id).recent_settled(after, before, limit)
    return [
        RecentLesson(
            id=row.id,
            title=row.title,
            status="ready" if row.status == "ready" else "failed",
            at=row.updated_at,
        )
        for row in rows
    ]
