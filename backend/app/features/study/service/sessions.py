"""Start of a guided session (SPEC F14, D103): "Start my block" (today's block) or a chosen
lesson, with or without a question for the Tutor.

Under the user's lock: the lesson (404 `lesson_not_found`, 409 `lesson_not_ready`) or today's
block (404 `no_block_today`, only if there is no open session: "Start my block" without a
block, with a live session, returns 409 `study_already_open` toward it); an `open` session
whose agent session is finished is stored as by a second "Finish" if its time was kept
("Finish" sent, Tutor stopped before concluding: final review of phase 5, S-I1), otherwise
becomes `cancelled` (with `ended_at`) in the same transaction as the insertion of the new one
(F11); a live session on the same lesson is returned as is (200), on another lesson: 409
`study_already_open` (`details.study_session_id`). The partial unique index settles a race that
would go through anyway: the second one re-reads the open session. The row is committed BEFORE
`launcher.start` (SQLite's write lock is never held during the launch, D66, D72); a refused
launch leaves the session `cancelled` (with `ended_at`). Logs: ids only."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.schemas import StudyStart, StudyStarted
from app.features.study.service.block import block_of_day, module_block
from app.features.study.service.finish import NO_OUTCOME, finish_study
from app.features.study.service.runtime import GRAPH, SUBJECT, StudyRuntime
from app.features.study.service.store import lesson_not_ready
from app.features.study.service.view import agent_status, is_dead

logger = logging.getLogger(__name__)


def lesson_not_found() -> AppError:
    return AppError("lesson_not_found", "Lesson not found.", 404)


def no_block_today() -> AppError:
    return AppError("no_block_today", "Nothing is scheduled today. Choose a lesson.", 404)


def study_already_open(study_id: str) -> AppError:
    return AppError(
        "study_already_open",
        "Finish the open study session on the other lesson before starting this one.",
        409,
        {"study_session_id": study_id},
    )


def training_already_open(study_id: str) -> AppError:
    return AppError(
        "study_already_open",
        "Finish the open training session before starting this one.",
        409,
        {"study_session_id": study_id, "kind": "training"},
    )


@dataclass(frozen=True)
class Target:
    lesson_id: str
    module_id: str
    program_id: str
    task_ids: list[str]


async def _target(
    rt: StudyRuntime, db: AsyncSession, user_id: str, body: StudyStart
) -> Target | None:
    """The start's target; `None`: "my block" without a block for today."""
    today = await rt.today(db, user_id)
    if body.lesson_id is None:
        block = await block_of_day(db, user_id, today)
        if block is None:
            return None
        return Target(block.lesson_id, block.module_id, block.program_id, block.task_ids)
    lesson = await StudyReadRepository(db, user_id).lesson(body.lesson_id)
    if lesson is None:
        raise lesson_not_found()
    if lesson.status != "ready":
        raise lesson_not_ready()
    tasks = await module_block(db, user_id, lesson.module_id, today)
    return Target(lesson.id, lesson.module_id, lesson.program_id, tasks)


async def _settle_kept(rt: StudyRuntime, user_id: str) -> None:
    """Under the lock, before the insertion: a dead open session whose time was kept ("Finish"
    sent, then the Tutor stopped before concluding) is stored as a second "Finish" would do
    (time, log, streak; without question results), never cancelled (final review of phase 5,
    S-I1). Lock order: study, then program (F4)."""
    async with rt.session_factory() as db:
        row = await StudyRepository(db, user_id).open_one()
        if row is None or row.kind != "guided" or row.worked_minutes is None:
            return
        status = await agent_status(db, user_id, row.session_id)
        dead = row.session_id is None or is_dead(row, status)
    if dead:
        await finish_study(rt, user_id, None, row.id, NO_OUTCOME)
        logger.info("End stored at the next start (Tutor stopped): study %s", row.id)


async def _live(db: AsyncSession, user_id: str, now: datetime) -> tuple[str, str, str] | None:
    """`(id, lesson, session)` of the open session still alive; a dead session (its agent
    session is finished, or its launch stopped: under the lock, a session without an agent
    session is no longer being launched) becomes `cancelled` (F11), not committed. A dead
    session with kept time has already been stored by `_settle_kept`."""
    repo = StudyRepository(db, user_id)
    row = await repo.open_one()
    if row is None:
        return None
    if row.kind == "training":
        raise training_already_open(row.id)
    status = await agent_status(db, user_id, row.session_id)
    if row.session_id is None or is_dead(row, status):
        await repo.close_open(row.id, status="cancelled", ended_at=now)
        logger.info("Interrupted study session cancelled: study %s", row.id)
        return None
    assert row.lesson_id is not None  # required target of a guided session
    return row.id, row.lesson_id, row.session_id


def _existing(live: tuple[str, str, str], lesson_id: str | None) -> StudyStarted:
    """The open session returned as is; another lesson, or no lesson (no block): 409."""
    study_id, open_lesson, session_id = live
    if open_lesson != lesson_id:
        raise study_already_open(study_id)
    return StudyStarted(study_session_id=study_id, session_id=session_id, lesson_id=lesson_id)


async def _insert(
    rt: StudyRuntime, user_id: str, body: StudyStart
) -> tuple[StudyStarted | None, str, str]:
    """Under the lock: `(session returned as is, None, None)` or `(None, id, lesson)` of the
    inserted and committed session."""
    async with rt.session_factory() as db:
        target = await _target(rt, db, user_id, body)
        live = await _live(db, user_id, rt.now())
        if live is not None:
            return _existing(live, target.lesson_id if target else None), "", ""
        if target is None:
            raise no_block_today()
        repo = StudyRepository(db, user_id)
        try:
            row = await repo.add(
                lesson_id=target.lesson_id,
                module_id=target.module_id,
                program_id=target.program_id,
                mode=body.mode,
                status="open",
                question=(body.question or "").strip() or None,
                task_ids=target.task_ids,
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            live = await _live(db, user_id, rt.now())
            if live is None:
                raise
            return _existing(live, target.lesson_id), "", ""
        return None, row.id, target.lesson_id


async def _set_session(rt: StudyRuntime, user_id: str, study_id: str, sid: str | None) -> None:
    async with rt.session_factory() as db:
        repo = StudyRepository(db, user_id)
        if sid is None:
            await repo.close_open(study_id, status="cancelled", ended_at=rt.now())
        else:
            await repo.update(study_id, session_id=sid)
        await db.commit()


async def start_study(
    rt: StudyRuntime, user_id: str, body: StudyStart
) -> tuple[StudyStarted, bool]:
    """Opens the session and launches the Tutor; returns `(start, created)` (202 if created)."""
    async with rt.study_lock(user_id):
        await _settle_kept(rt, user_id)
        existing, study_id, lesson_id = await _insert(rt, user_id, body)
        if existing is not None:
            return existing, False
        try:
            sid = await rt.launcher.start(
                user_id,
                GRAPH,
                {"study_session_id": study_id},
                subject_type=SUBJECT,
                subject_id=study_id,
            )
        except BaseException:
            await _set_session(rt, user_id, study_id, None)
            raise
        await _set_session(rt, user_id, study_id, sid)
    logger.info("Study session opened: study %s, session %s", study_id, sid)
    return StudyStarted(study_session_id=study_id, session_id=sid, lesson_id=lesson_id), True
