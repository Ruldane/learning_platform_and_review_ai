"""End and abandonment of a guided session (`PATCH`, SPEC 14.2; D103 no. 2, 3), under the user's
lock. A session already finished or abandoned is returned as is (idempotent).

"Finish": the front end's timer (`worked_minutes`, absent: 0) is kept, bounded by the real
duration since the start (rounded up to the minute) and never below the time already kept (a
second "Finish" without a timer does not erase it), THEN the waiting question receives
`{"action": "finish"}` whatever its kind (`tutor_question` or `finish_session`): the Tutor
makes its summary and stores the end through the port (`finish.py`). End already requested
(time kept, Tutor concluding): state returned; time kept but question still waiting (back-end
stop before the resume): resume. Tutor writing (no question waiting): 409 `study_not_waiting`,
nothing is kept. Agent session ended on the way (failure, cancellation): the route stores the
end itself, without question results, so that the time counts.

"Abandon": the session becomes `cancelled` (nothing else: no time, task or card), then its
agent session is cancelled."""

import logging
import math
from datetime import datetime

from app.agents.runtime.handle import AgentRuntime
from app.core.errors import AppError
from app.db.models.study import StudySession
from app.features.sessions.service import ResumeRequest, SessionsService, SessionView
from app.features.study.repository import StudyRepository
from app.features.study.schemas import StudySessionOut, StudyUpdate
from app.features.study.service.finish import NO_OUTCOME, finish_study
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.view import is_dead, read_row, session_out

logger = logging.getLogger(__name__)

FINISH = {"action": "finish"}


def study_not_waiting(status: str) -> AppError:
    return AppError(
        "study_not_waiting",
        "The tutor is still writing. You can finish after the next question.",
        409,
        {"status": status},
    )


def clamped_minutes(worked: int | None, started: datetime, now: datetime) -> int:
    """`min(timer, real duration rounded up to the minute)`, never negative."""
    elapsed = max(0.0, (now - started).total_seconds())
    return max(0, min(worked or 0, math.ceil(elapsed / 60)))


async def _keep_minutes(
    rt: StudyRuntime, user_id: str, row: StudySession, worked: int | None
) -> None:
    # Absent never erases the time already kept (a second "Finish" without a timer).
    minutes = max(row.worked_minutes or 0, clamped_minutes(worked, row.created_at, rt.now()))
    async with rt.session_factory() as db:
        await StudyRepository(db, user_id).close_open(row.id, worked_minutes=minutes)
        await db.commit()


async def _forget_minutes(rt: StudyRuntime, user_id: str, row: StudySession) -> None:
    """The resume failed: the time goes back to what it was before THIS click (a time kept by a
    previous "Finish" is never erased; final review of phase 5, S-m5)."""
    async with rt.session_factory() as db:
        await StudyRepository(db, user_id).close_open(row.id, worked_minutes=row.worked_minutes)
        await db.commit()


async def _agent_view(
    runtime: AgentRuntime, rt: StudyRuntime, user_id: str, session_id: str
) -> SessionView:
    async with rt.session_factory() as db:
        return await SessionsService(db, user_id, runtime).get(session_id)


async def _resume(
    runtime: AgentRuntime, rt: StudyRuntime, user_id: str, session_id: str, interrupt_id: str
) -> None:
    request = ResumeRequest(interrupt_id=interrupt_id, value=FINISH)
    async with rt.session_factory() as db:
        await SessionsService(db, user_id, runtime).resume(session_id, request)


async def _finish(
    runtime: AgentRuntime,
    rt: StudyRuntime,
    user_id: str,
    row: StudySession,
    status: str | None,
    worked: int | None,
) -> None:
    if row.session_id is None or is_dead(row, status):
        await _keep_minutes(rt, user_id, row, worked)
        await finish_study(rt, user_id, None, row.id, NO_OUTCOME)
        logger.info("End stored by the route (Tutor stopped): study %s", row.id)
        return
    view = await _agent_view(runtime, rt, user_id, row.session_id)
    pending = view.pending_interrupt
    if view.status != "waiting_user" or pending is None:
        if row.worked_minutes is not None:
            return  # end already requested: the Tutor concludes
        raise study_not_waiting(view.status)
    # Still waiting (time kept then back-end stop before the resume): we resume.
    await _keep_minutes(rt, user_id, row, worked)
    try:
        await _resume(runtime, rt, user_id, row.session_id, pending.interrupt_id)
    except BaseException as exc:
        await _forget_minutes(rt, user_id, row)
        if isinstance(exc, AppError) and exc.code == "stale_interrupt":
            raise study_not_waiting(
                (await _agent_view(runtime, rt, user_id, row.session_id)).status
            ) from None
        raise
    logger.info("End requested: study %s, session %s", row.id, row.session_id)


async def _cancel(runtime: AgentRuntime, rt: StudyRuntime, user_id: str, row: StudySession) -> None:
    async with rt.session_factory() as db:
        closed = await StudyRepository(db, user_id).close_open(
            row.id, status="cancelled", ended_at=rt.now()
        )
        await db.commit()
    if not closed or row.session_id is None:
        return
    try:
        async with rt.session_factory() as db:
            await SessionsService(db, user_id, runtime).cancel(row.session_id)
    except AppError as exc:  # already finished or not found: nothing to stop
        if exc.code not in ("session_not_cancellable", "session_not_found"):
            raise
    logger.info("Study session abandoned: study %s", row.id)


async def update_study(
    runtime: AgentRuntime, rt: StudyRuntime, user_id: str, study_id: str, body: StudyUpdate
) -> StudySessionOut:
    """ "Finish" or "Abandon" (see the module); 404 for another user's session."""
    async with rt.study_lock(user_id):
        async with rt.session_factory() as db:
            row, status = await read_row(db, user_id, study_id)
        if row.status == "open" and body.action == "cancel":
            await _cancel(runtime, rt, user_id, row)
        elif row.status == "open":
            await _finish(runtime, rt, user_id, row, status, body.worked_minutes)
    async with rt.session_factory() as db:
        return await session_out(db, user_id, study_id)
