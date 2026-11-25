"""Reads of guided study (D103 #4, 5): the state of a session (end screen) and the summary (streak,
hours of the week, timer, open session, day's block). Local days and weeks (January's time zone,
D98).

An `open` session whose agent session has ended (failure, cancellation) or cannot be found is
shown `interrupted`, without writing (D91, F11); the database is corrected only under the user's
lock (new start, "Finish"). Order of reads (D97 #9): the agent session, THEN the row re-read: a
session finished between the two reads is never shown as interrupted."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone, week_start
from app.db.models.study import StudySession
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.schemas import StudySessionOut, StudySummaryOut
from app.features.study.service.block import block_of_day
from app.features.study.service.finish import finished_of, study_not_found
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.streak import streak

TERMINAL = frozenset({"completed", "failed", "cancelled", "expired"})


async def agent_status(db: AsyncSession, user_id: str, session_id: str | None) -> str | None:
    """Status of the agent session (`None`: not yet stored, or not found)."""
    if session_id is None:
        return None
    facts = await session_facts(db, user_id, session_id)
    return facts.status if facts is not None else "missing"


def is_dead(row: StudySession, status: str | None) -> bool:
    """Session still `open` whose agent session is no longer running."""
    return (
        row.status == "open" and status is not None and (status in TERMINAL or status == "missing")
    )


async def read_row(
    db: AsyncSession, user_id: str, study_id: str
) -> tuple[StudySession, str | None]:
    """`(row, status of its agent session)` in the safe order; 404 for another user's."""
    repo = StudyRepository(db, user_id)
    first = await repo.get_fresh(study_id)
    if first is None or first.kind != "guided":
        raise study_not_found()
    status = await agent_status(db, user_id, first.session_id)
    row = await repo.get_fresh(study_id)
    if row is None:
        raise study_not_found()
    if row.session_id != first.session_id:
        status = await agent_status(db, user_id, row.session_id)
    return row, status


async def session_out(db: AsyncSession, user_id: str, study_id: str) -> StudySessionOut:
    row, status = await read_row(db, user_id, study_id)
    lesson_title, module_title = await StudyReadRepository(db, user_id).titles(
        row.lesson_id, row.module_id
    )
    done = finished_of(row)
    return StudySessionOut.model_validate(
        {
            "id": row.id,
            "lesson_id": row.lesson_id,
            "lesson_title": lesson_title,
            "module_title": module_title,
            "mode": row.mode,
            "status": "interrupted" if is_dead(row, status) else row.status,
            "session_id": row.session_id,
            "started_at": row.created_at,
            "ended_at": row.ended_at,
            "minutes": row.minutes,
            "summary": row.summary,
            "tasks_done": done.tasks_done,
            "flashcards_created": done.flashcards_created,
            "skills": [{"name": name, "level": level} for name, level in done.skills],
        }
    )


def _local(moment: datetime, zone: ZoneInfo) -> datetime:
    return moment.astimezone(zone)


async def _open_live(db: AsyncSession, user_id: str) -> str | None:
    """The open session still alive. A dead session (read as `interrupted`, D91) is not offered for
    resumption: the home screen offers a new start, which stores or cancels it (final review of
    phase 5, front-end review I1)."""
    current = await StudyRepository(db, user_id).open_one()
    if current is None or current.kind != "guided":
        return None
    if is_dead(current, await agent_status(db, user_id, current.session_id)):
        return None
    return current.id


async def summary(rt: StudyRuntime, db: AsyncSession, user_id: str) -> StudySummaryOut:
    settings = await SettingsService(db, user_id).get()
    zone = user_zone(settings.timezone)
    today = local_today(zone, rt.now())
    monday = week_start(today)
    ended = [
        (_local(at, zone).date(), minutes)
        for at, minutes in await StudyRepository(db, user_id).finished()
    ]
    week = sum(m for day, m in ended if monday <= day < monday + timedelta(days=7))
    block = await block_of_day(db, user_id, today)
    return StudySummaryOut(
        streak_days=streak({day for day, _ in ended}, today),
        week_minutes=week,
        work_minutes=settings.study_work_minutes,
        break_minutes=settings.study_break_minutes,
        open_session_id=await _open_live(db, user_id),
        block=block.out() if block is not None else None,
    )
