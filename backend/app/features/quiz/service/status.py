"""Status of a quiz or an attempt as it is shown (D101, same reason as D91).

A `quiz` session that stops outside the port (unreadable output three times, timeout,
cancellation) leaves its quiz `generating` or its attempt `grading`. Each read already shows
them as failed, without writing; the database is only corrected under the quiz lock (relaunch,
new attempt). A `generating` quiz without a stored session (stop between the row and the
launch) is read as failed too, so that "Relaunch" stays possible; a `grading` attempt without a
session stays as it is (launch in progress).

Order of reads (D97 no. 9): open sessions, THEN rows. If a row looks interrupted, the sessions
are re-read: the one launched between the two reads counts as open."""

from collections.abc import Awaitable, Callable, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.quiz.service.runtime import GRAPH, SUBJECT
from app.features.sessions.service import list_open_sessions, list_open_sessions_by_subject

QUIZ_INTERRUPTED = "Quiz preparation stopped early. Restart it to continue."
# A hand-written quiz that does not yet have the Examiner's bounds (`quiz_gaps`) stays "being
# prepared": `generating`, without a session, with this reason; it is not an interrupted
# preparation.
DRAFT_REASON = "This draft needs more questions before you can take the quiz."
_LEGACY_DRAFT_REASON = (
    "En cours d'écriture : il manque des questions avant de pouvoir répondre au quiz."
)
LIVE = {"generating", "grading"}


def is_draft_reason(reason: str | None) -> bool:
    return reason in {DRAFT_REASON, _LEGACY_DRAFT_REASON}


async def open_sessions(db: AsyncSession, user_id: str, quiz_id: str) -> list[str]:
    """`quiz` sessions open on this quiz (writing the quiz or grading an attempt)."""
    return await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=quiz_id
    )


async def open_sessions_by_quiz(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    """The user's open `quiz` sessions, per quiz, in one query (lists)."""
    return await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)


def interrupted(
    status: str, session_id: str | None, open_ids: list[str], reason: str | None = None
) -> bool:
    """`generating` quiz or `grading` attempt whose stored session is no longer open
    (finished without the port, failed, cancelled), or `generating` quiz without a stored
    session."""
    if status not in LIVE or is_draft_reason(reason):
        return False
    if session_id is None:
        return status == "generating"
    return session_id not in open_ids


async def read_with_sessions[R](
    db: AsyncSession,
    user_id: str,
    quiz_id: str,
    read: Callable[[], Awaitable[R]],
    states: Callable[[R], Iterable[tuple[str, str | None]]],
) -> tuple[R, list[str]]:
    """`(rows read by read, open sessions of the quiz)` in the safe order."""
    open_ids = await open_sessions(db, user_id, quiz_id)
    rows = await read()
    if any(interrupted(st, sid, open_ids) for st, sid in states(rows)):
        later = await open_sessions(db, user_id, quiz_id)
        open_ids += [sid for sid in later if sid not in open_ids]
    return rows, open_ids


def quiz_shown(
    status: str, session_id: str | None, reason: str | None, open_ids: list[str]
) -> tuple[str, str | None]:
    """`(status, reason)` of the quiz to show."""
    if interrupted(status, session_id, open_ids, reason):
        return "failed", QUIZ_INTERRUPTED
    return status, DRAFT_REASON if is_draft_reason(reason) else reason


def attempt_shown(status: str, session_id: str | None, open_ids: list[str]) -> str:
    return "failed" if interrupted(status, session_id, open_ids) else status
