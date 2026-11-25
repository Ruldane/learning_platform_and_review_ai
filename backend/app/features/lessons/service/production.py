"""Chained lesson production (SPEC 3.5, 3.6; D90, D91).

A single `lesson_factory` chain per program, one module at a time (no burst of model calls):
`ensure_lessons` starts the lesson of the first due module if no lesson session is open for the
program. It is called by the validation (weeks 1 and 2 right away), by the end of each lesson
(`next_module`, which excludes its own session) and by the scheduled job (later weeks 7 days
before they start). Everything runs under the program's lessons lock: two simultaneous calls
never start two sessions, nor two lessons for one module.

A lesson session that stops without going through the port (invalid Verifier, quota,
cancellation…) leaves its lesson `generating`: the lesson is marked failed on the next call (its
session is no longer open), at the latest on the job's next run (15 minutes); reads show it as
failed as soon as it stops (`status`). A failed lesson is retried while it has had fewer than
`MAX_ATTEMPTS` attempts, after the modules never attempted. With nothing due, a call only reads
the database: no write, no start, no model call. Logs: identifiers only."""

import logging
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.played import inherit_source
from app.db.models.lessons import MAX_LESSON_ATTEMPTS, Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.service.runtime import Launcher
from app.features.lessons.service.status import GRAPH, INTERRUPTED, SUBJECT
from app.features.program.service.module_kinds import has_lesson
from app.features.program.service.programs import Loaded, list_validated_programs, load
from app.features.sessions.service import list_open_sessions, session_facts

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = MAX_LESSON_ATTEMPTS
HORIZON_DAYS = 7
FIRST_WEEKS = (1, 2)


class ProductionContext(Protocol):
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]: ...

    @property
    def launcher(self) -> Launcher: ...

    def lessons_lock(self, user_id: str, program_id: str) -> AbstractAsyncContextManager[None]: ...


@dataclass(frozen=True)
class _Pick:
    lesson_id: str
    module_id: str
    # Previous status, attempts and reason: restored if the start fails.
    previous: tuple[str, int, str | None]
    played_by: str | None
    model_provider: str | None
    has_origin: bool


def week_due(rank: int, start: date, today: date) -> bool:
    """Weeks 1 and 2 right away, later ones from 7 days before they start (UTC)."""
    return rank in FIRST_WEEKS or start <= today + timedelta(days=HORIZON_DAYS)


def _missing_lessons(db: AsyncSession, user_id: str, loaded: Loaded, have: set[str]) -> int:
    """A `pending` lesson for each planned module that has none (lessons list); returns the
    number of lessons added (zero outside the first pass after validation)."""
    missing = [m for m in loaded.modules if has_lesson(m) and m.id not in have]
    for module in missing:
        db.add(
            Lesson(
                user_id=user_id,
                module_id=module.id,
                program_id=loaded.program.id,
                title=module.title[:200],
                status="pending",
            )
        )
    return len(missing)


def _reconcile(lessons: list[Lesson], open_ids: list[str]) -> int:
    """A `generating` lesson whose session is no longer open: failed (retried later)."""
    stale = [
        x
        for x in lessons
        if x.status == "generating"
        and x.session_id not in open_ids
        and x.verification_session_id is None
    ]
    for lesson in stale:
        lesson.status, lesson.failure_reason = "failed", INTERRUPTED
    return len(stale)


def _first_due(loaded: Loaded, lessons: dict[str, Lesson], today: date) -> Lesson | None:
    """First due module: never-attempted ones first, then failed; by week then rank."""
    weeks = {week.id: week for week in loaded.weeks}
    due: list[tuple[bool, int, Lesson]] = []
    for index, module in enumerate(loaded.modules):
        week = weeks.get(module.week_id)
        lesson = lessons.get(module.id)
        if not has_lesson(module) or week is None or lesson is None:
            continue
        if lesson.status not in ("pending", "failed") or lesson.attempts >= MAX_ATTEMPTS:
            continue
        if lesson.verification_failure_reason is not None:
            continue  # a rejected manual submission is fixed then submitted again
        if week_due(week.rank, week.start_date, today):
            due.append((lesson.status == "failed", index, lesson))
    return min(due, key=lambda item: (item[0], item[1]))[2] if due else None


async def _prepare(
    db: AsyncSession, user_id: str, program_id: str, exclude: str | None, today: date
) -> _Pick | None:
    loaded = await load(db, user_id, program_id)
    if loaded.program.status != "validated":
        return None
    repo = LessonRepository(db, user_id)
    rows = await repo.for_program(program_id)
    if _missing_lessons(db, user_id, loaded, {x.module_id for x in rows}):
        await db.flush()
        rows = await repo.for_program(program_id)
    open_ids = await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=program_id
    )
    if stale := _reconcile(rows, open_ids):
        logger.info("Interrupted lessons: program %s, %d failed", program_id, stale)
    if any(session_id != exclude for session_id in open_ids):
        return None  # a chain is already running for this program
    lesson = _first_due(loaded, {x.module_id: x for x in rows}, today)
    if lesson is None:
        return None
    parent = loaded.program.session_id
    source = await session_facts(db, user_id, parent) if parent else None
    pick = _Pick(
        lesson.id,
        lesson.module_id,
        (lesson.status, lesson.attempts, lesson.failure_reason),
        source.played_by if source else None,
        source.model_provider if source else None,
        source is not None,
    )
    lesson.status, lesson.attempts = "generating", lesson.attempts + 1
    lesson.failure_reason, lesson.session_id = None, None
    return pick


async def _set_session(ctx: ProductionContext, user_id: str, pick: _Pick, sid: str | None) -> None:
    """Stores the started session on the lesson; `None`: failed start, previous state restored."""
    async with ctx.session_factory() as db:
        lesson = await LessonRepository(db, user_id).get_fresh(pick.lesson_id)
        if lesson is not None:
            if sid is None:
                lesson.status, lesson.attempts, lesson.failure_reason = pick.previous
            else:
                lesson.session_id = sid
        await db.commit()


async def ensure_lessons(
    ctx: ProductionContext,
    user_id: str,
    program_id: str,
    *,
    exclude_session_id: str | None = None,
    today: date | None = None,
) -> str | None:
    """Starts the lesson of the first due module if no other lesson session is open for the
    program; returns the started session's id, `None` otherwise. Someone else's program: 404.
    Start refused (engine unavailable): the lesson gets its state back and the error propagates."""
    day = today or datetime.now(UTC).date()
    async with ctx.lessons_lock(user_id, program_id):
        async with ctx.session_factory() as db:
            pick = await _prepare(db, user_id, program_id, exclude_session_id, day)
            await db.commit()
        if pick is None:
            return None
        payload = {"program_id": program_id, "module_id": pick.module_id}
        try:
            with inherit_source(
                user_id, pick.played_by, pick.model_provider, has_origin=pick.has_origin
            ):
                sid = await ctx.launcher.start(
                    user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=program_id
                )
        except BaseException:
            await _set_session(ctx, user_id, pick, None)
            raise
        await _set_session(ctx, user_id, pick, sid)
    logger.info(
        "Lesson started: user %s, program %s, module %s, session %s",
        user_id,
        program_id,
        pick.module_id,
        sid,
    )
    return sid


async def start_lessons(ctx: ProductionContext, user_id: str, program_id: str) -> None:
    """`ensure_lessons` without ever raising (after a validation): a failure is logged by its
    type, the scheduled job will catch up."""
    try:
        await ensure_lessons(ctx, user_id, program_id)
    except Exception as exc:
        logger.warning("Lessons not started: program %s (%s)", program_id, type(exc).__name__)


async def list_programs_due(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[tuple[str, str]]:
    """`(user, program)` of validated programs: the phase's only read without `user_id`,
    reserved for the scheduled job (D91), identifiers only."""
    async with session_factory() as db:
        return await list_validated_programs(db)
