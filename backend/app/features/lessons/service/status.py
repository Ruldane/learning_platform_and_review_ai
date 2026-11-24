"""A lesson's status as it is shown (D91).

A `lesson_factory` session that stops outside the port (invalid Verifier, quota, cancellation)
leaves its lesson `generating`. The database is only corrected under the program's lessons lock
(`ensure_lessons`, at the latest on the scheduled job's next run); until then, every read
already shows the lesson as failed, without writing anything. A `generating` lesson with no
session stored yet is being started: it stays `generating`.

Read order (`read_with_open_sessions`, D97): open sessions, THEN lesson rows. A lesson finished
in between is read as ready (publication precedes the end of its session): never shown as
failed. If a lesson looks interrupted, the sessions are read again after the rows: the session
of a lesson started between the two reads then counts as open."""

import builtins
from collections.abc import Awaitable, Callable, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sessions.service import list_open_sessions

GRAPH = "lesson_factory"
SUBJECT = "program"
INTERRUPTED = "The lesson production stopped before the end: it will be retried."
VERIFICATION_INTERRUPTED = "The draft verification stopped before publication."


async def open_lesson_sessions(
    db: AsyncSession, user_id: str, program_id: str
) -> builtins.list[str]:
    """The program's open lesson sessions (at most one in normal times)."""
    return await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=program_id
    )


async def read_with_open_sessions[R](
    db: AsyncSession,
    user_id: str,
    program_id: str,
    read: Callable[[], Awaitable[R]],
    states: Callable[[R], Iterable[tuple[str, str | None]]],
) -> tuple[R, builtins.list[str]]:
    """`(rows read by read, open sessions)` in the safe order; `states` gives
    `(status, session)` for each lesson read."""
    open_ids = await open_lesson_sessions(db, user_id, program_id)
    rows = await read()
    if any(interrupted(st, sid, open_ids) for st, sid in states(rows)):
        later = await open_lesson_sessions(db, user_id, program_id)
        open_ids += [sid for sid in later if sid not in open_ids]
    return rows, open_ids


def interrupted(status: str, session_id: str | None, open_ids: builtins.list[str]) -> bool:
    """A `generating` lesson whose stored session is no longer open (finished, failed,
    cancelled)."""
    return status == "generating" and session_id is not None and session_id not in open_ids


def shown(
    status: str, session_id: str | None, reason: str | None, open_ids: builtins.list[str]
) -> tuple[str, str | None]:
    """`(status, reason)` to show: an interrupted lesson appears as failed."""
    if interrupted(status, session_id, open_ids):
        return "failed", INTERRUPTED
    return status, reason
