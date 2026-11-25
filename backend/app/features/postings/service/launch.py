"""Launching a posting's analysis (`gap_analysis` flow, D121, D122), under the posting's lock:
a single session at a time. `gap_session_id` is set as soon as the session exists; a launch
that fails sets the posting to `failed` (fixed reason) before raising the error. A refused,
failed, interrupted or gapless posting is relaunched: status reset to `analyzing` (or `ready`
if its analysis is stored), reason cleared. Logs: ids only."""

import logging

from app.core.errors import AppError
from app.features.postings.repository import PostingRepository
from app.features.postings.service.duplicates import not_found
from app.features.postings.service.runtime import GRAPH, SUBJECT, PostingsRuntime
from app.features.postings.service.status import (
    LAUNCH_FAILED,
    needs_launch,
    open_sessions,
    running,
)

logger = logging.getLogger(__name__)


def gap_in_progress() -> AppError:
    return AppError("gap_in_progress", "This posting is already being analyzed.", 409)


async def _set_session(rt: PostingsRuntime, user_id: str, posting_id: str, sid: str | None) -> None:
    async with rt.session_factory() as db:
        posting = await PostingRepository(db, user_id).get_fresh(posting_id)
        if posting is None:
            return
        if sid is not None:
            posting.gap_session_id = sid
        else:
            posting.status, posting.failure_reason = "failed", LAUNCH_FAILED
        await db.commit()


async def _start(rt: PostingsRuntime, user_id: str, posting_id: str) -> str:
    """To be called under the posting's lock."""
    try:
        sid = await rt.launcher.start(
            user_id, GRAPH, {"posting_id": posting_id}, subject_type=SUBJECT, subject_id=posting_id
        )
    except BaseException:
        await _set_session(rt, user_id, posting_id, None)
        logger.warning("Posting analysis not started: user %s, posting %s", user_id, posting_id)
        raise
    await _set_session(rt, user_id, posting_id, sid)
    logger.info(
        "Posting analysis started: user %s, posting %s, session %s", user_id, posting_id, sid
    )
    return sid


async def launch_new(rt: PostingsRuntime, user_id: str, posting_id: str) -> str:
    """The analysis of a posting that has just been added."""
    async with rt.launch_locks.get(user_id, posting_id):
        return await _start(rt, user_id, posting_id)


async def relaunch(
    rt: PostingsRuntime, user_id: str, posting_id: str, *, if_needed: bool
) -> str | None:
    """Relaunches the analysis. `if_needed` (posting sent again): only if `needs_launch`,
    otherwise `None`. Without it (`POST /postings/{id}/gap`): always, except a session in
    progress (409 `gap_in_progress`). Absent posting or another user's: 404."""
    async with rt.launch_locks.get(user_id, posting_id):
        async with rt.session_factory() as db:
            open_ids = await open_sessions(db, user_id, posting_id)
            posting = await PostingRepository(db, user_id).get_fresh(posting_id)
            if posting is None:
                raise not_found()
            if running(posting, open_ids):
                if if_needed:
                    return None
                raise gap_in_progress()
            if if_needed and not needs_launch(posting, open_ids):
                return None
            posting.status = "analyzing" if posting.analysis is None else "ready"
            posting.failure_reason, posting.gap_session_id = None, None
            await db.commit()
        return await _start(rt, user_id, posting_id)
