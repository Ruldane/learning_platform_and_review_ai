"""Status of a posting and of its gap, as they are shown (D122, same reason as D91 and D101).

A `gap_analysis` session that stops outside the port (unreadable output, timeout, cancellation,
server shutdown) leaves its posting `analyzing`, or `ready` without a gap. Each read already
shows it as failed, with `gap_session_id`, without writing; the database is only corrected on
a retry (new submission of the same link or text, `POST /postings/{id}/gap`), under the
posting's lock.

Order of reads (D97 no. 9): open sessions, THEN rows; if a row looks interrupted, the sessions
are read again (a session started between the two reads counts as open)."""

from collections.abc import Awaitable, Callable, Iterable
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.postings import JobPosting
from app.features.postings.service.runtime import GRAPH, SUBJECT
from app.features.sessions.service import list_open_sessions, list_open_sessions_by_subject

INTERRUPTED = "Posting analysis stopped. Restart the analysis."
LAUNCH_FAILED = "Posting analysis could not start. Restart the analysis."
GapStatus = Literal["pending", "ready", "failed"]


async def open_sessions(db: AsyncSession, user_id: str, posting_id: str) -> list[str]:
    return await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=posting_id
    )


async def open_sessions_by_posting(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    return await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)


def running(posting: JobPosting, open_ids: Iterable[str]) -> bool:
    """The session stored on the posting is still running."""
    return posting.gap_session_id is not None and posting.gap_session_id in set(open_ids)


def interrupted(posting: JobPosting, open_ids: Iterable[str]) -> bool:
    """Posting under analysis whose session is no longer open (or was never stored)."""
    return posting.status == "analyzing" and not running(posting, open_ids)


def shown_status(posting: JobPosting, open_ids: Iterable[str]) -> tuple[str, str | None]:
    """`(status, reason)` of the posting to show."""
    if interrupted(posting, open_ids):
        return "failed", INTERRUPTED
    return posting.status, posting.failure_reason


def gap_status(posting: JobPosting, open_ids: Iterable[str]) -> GapStatus:
    """`ready`: the gap of the stored session is written (or an older one, if nothing is running
    anymore); `pending`: the session is running; otherwise `failed` (refused posting included)."""
    gap = posting.gap
    if posting.status == "rejected":
        return "failed"
    if gap is not None and gap.get("session_id") == posting.gap_session_id:
        return "ready"
    if running(posting, open_ids):
        return "pending"
    return "ready" if gap is not None else "failed"


def needs_launch(posting: JobPosting, open_ids: Iterable[str]) -> bool:
    """A posting already added is re-run rather than returned as is if it is refused, failed,
    interrupted, or analysed without a gap while nothing is running anymore."""
    if posting.status in ("rejected", "failed"):
        return True
    return not running(posting, open_ids) and posting.gap is None


async def read_with_sessions[R](
    db: AsyncSession,
    user_id: str,
    read: Callable[[], Awaitable[R]],
    postings: Callable[[R], Iterable[JobPosting]],
) -> tuple[R, dict[str, list[str]]]:
    """`(rows read by read, open sessions per posting)`, in the safe order."""
    open_ids = await open_sessions_by_posting(db, user_id)
    rows = await read()
    if any(needs_launch(p, open_ids.get(p.id, [])) for p in postings(rows)):
        later = await open_sessions_by_posting(db, user_id)
        for key, ids in later.items():
            open_ids[key] = list(dict.fromkeys([*open_ids.get(key, []), *ids]))
    return rows, open_ids
