"""Mock interviews on the API side (SPEC F10, D146): launching the `interview` flow from a
record or freely (posting or title alone), list and detail.

- One open interview per user (409 `interview_in_progress`, `details.interview_id`), under the
  interviews lock; the interview is stored (`running`) BEFORE the launch: the flow re-reads it
  in its own session. A launch refused by the engine sets it to `failed`.
- The status follows the outcome of the session (as D129 no. 5): a `running` interview whose
  session is no longer open (crash, timeout, cancellation) becomes `failed` on the next read,
  under the lock; a finished session never resumes, so the fix is safe. `done`, `stopped` and
  `debrief_failed` are set by the port (`interview_store`) and no longer change.

Logs: ids and statuses only, never the title, a question or an answer."""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.negotiation import SalarySample, salary_outcome
from app.core.errors import AppError
from app.db.models.applications import Interview
from app.features.applications.repository import ApplicationRepository
from app.features.applications.repository_interviews import InterviewRepository
from app.features.applications.schemas_interviews import (
    DebriefOut,
    ExchangeOut,
    FreeInterviewIn,
    InterviewIn,
    InterviewOut,
    InterviewStartOut,
)
from app.features.applications.service.interview_context import DEFAULT_ROLE
from app.features.applications.service.kit_store import profile_required
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application, invalid, not_found
from app.features.cv.service.versions import validated_profile
from app.features.postings.service.queries import get_posting
from app.features.radar.service.runs import defaults as radar_defaults
from app.features.radar.service.salary_sample import radar_salary
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

GRAPH = "interview"
SUBJECT = "interview"


def interview_not_found() -> AppError:
    return AppError("interview_not_found", "Interview not found.", 404)


def interview_in_progress(interview_id: str) -> AppError:
    return AppError(
        "interview_in_progress",
        "Finish or stop the mock interview already in progress before starting another one.",
        409,
        {"interview_id": interview_id},
    )


def interview_lock(rt: ApplicationsRuntime, user_id: str) -> asyncio.Lock:
    """One lock per user: launch, stored result and read never interleave."""
    return rt.locks.get(user_id, "interviews")


async def interview_row(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
    """The user's interview, re-read from the database; 404 `interview_not_found` otherwise."""
    row = await InterviewRepository(db, user_id).get_fresh(interview_id)
    if row is None:
        raise interview_not_found()
    return row


async def settle(db: AsyncSession, user_id: str) -> None:
    """Running interviews without an open session → `failed`. Sessions read BEFORE the
    interviews (D97 no. 9). The caller holds `interview_lock`."""
    open_ids = await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)
    stale = [
        row
        for row in await InterviewRepository(db, user_id).running()
        if row.session_id not in open_ids.get(row.id, [])
    ]
    for row in stale:
        row.status = "failed"
        logger.info("Interview without session: user %s, interview %s", user_id, row.id)
    if stale:
        await db.commit()


def interview_out(row: Interview) -> InterviewOut:
    """The interview for the API: `flags` and `cards_created` are stored with the debrief."""
    data: dict[str, Any] = dict(row.debrief or {})
    flags = [str(flag) for flag in data.pop("flags", [])]
    cards_created = int(data.pop("cards_created", 0))
    salary = SalarySample.model_validate(row.salary) if row.salary is not None else None
    outcome = None
    if salary is not None and row.status in ("done", "debrief_failed") and row.exchanges:
        outcome = salary_outcome(
            salary, any(item.get("salary_raised") is True for item in row.exchanges)
        )
    return InterviewOut.model_validate(
        {
            "id": row.id,
            "application_id": row.application_id,
            "posting_id": row.posting_id,
            "role": row.role,
            "mode": row.mode,
            "duration_min": row.duration_min,
            "language": row.language,
            "session_id": row.session_id,
            "status": row.status,
            "exchanges": [ExchangeOut.model_validate(item) for item in row.exchanges],
            "debrief": DebriefOut.model_validate(data) if data else None,
            "flags": flags,
            "cards_created": cards_created,
            "created_at": row.created_at,
            "salary": salary,
            "salary_outcome": outcome,
        }
    )


async def _salary_snapshot(
    db: AsyncSession, user_id: str, setup: InterviewIn, role: str | None
) -> SalarySample | None:
    if setup.mode != "salary":
        return None
    default_role, default_zone = await radar_defaults(db, user_id)
    sample = await radar_salary(
        db, user_id, setup.radar_role or role or default_role, setup.radar_zone or default_zone
    )
    if sample is None:
        raise AppError(
            "radar_salary_missing",
            "The radar has no usable gross annual salary in euros for this role and location.",
            409,
        )
    return sample


async def require_interview_available(db: AsyncSession, user_id: str) -> None:
    await settle(db, user_id)
    rows = await InterviewRepository(db, user_id).running()
    if running := [row for row in rows if row.system_design is None]:
        raise interview_in_progress(running[0].id)
    if await validated_profile(db, user_id) is None:
        raise profile_required()


async def _launch(
    rt: ApplicationsRuntime,
    db: AsyncSession,
    user_id: str,
    setup: InterviewIn,
    *,
    application_id: str | None,
    posting_id: str | None,
    role: str | None,
) -> InterviewStartOut:
    """Input checks, interview stored, flow launched. Under the lock, in `db`."""
    await require_interview_available(db, user_id)
    repo = InterviewRepository(db, user_id)
    salary = await _salary_snapshot(db, user_id, setup, role)
    row = await repo.add(
        application_id=application_id,
        posting_id=posting_id,
        role=role,
        mode=setup.mode,
        duration_min=setup.duration_min,
        language=setup.language,
        salary=salary.model_dump(mode="json") if salary is not None else None,
        session_id="",  # set as soon as the flow is launched (the column is required)
        status="running",
    )
    await db.commit()  # the flow re-reads the interview in its own session
    try:
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"interview_id": row.id}, subject_type=SUBJECT, subject_id=row.id
        )
    except BaseException:
        row.status = "failed"
        await db.commit()
        logger.warning("Interview not started: user %s, interview %s", user_id, row.id)
        raise
    row.session_id = session_id
    await db.commit()
    logger.info(
        "Interview started: user %s, interview %s, session %s, %s, %d min",
        user_id,
        row.id,
        session_id,
        setup.mode,
        setup.duration_min,
    )
    return InterviewStartOut(interview_id=row.id, session_id=session_id)


async def start_for_application(
    rt: ApplicationsRuntime, user_id: str, application_id: str, body: InterviewIn
) -> InterviewStartOut:
    """Launches the interview of a record (404 `application_not_found`)."""
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        application = await get_application(db, user_id, application_id)
        return await _launch(
            rt,
            db,
            user_id,
            body,
            application_id=application.id,
            posting_id=application.posting_id,
            role=application.title,
        )


async def start_free(
    rt: ApplicationsRuntime, user_id: str, body: FreeInterviewIn
) -> InterviewStartOut:
    """Launches an interview without a record, on a posting (404 `posting_not_found`) or a title."""
    if (body.posting_id is None) == (body.role is None):
        raise invalid("posting_id", "role")  # one or the other, never both
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        role = body.role
        if body.posting_id is not None:
            posting = await get_posting(db, user_id, body.posting_id)
            role = posting.title or DEFAULT_ROLE
        return await _launch(
            rt, db, user_id, body, application_id=None, posting_id=body.posting_id, role=role
        )


async def list_interviews(
    rt: ApplicationsRuntime, user_id: str, application_id: str | None
) -> list[InterviewOut]:
    """The interviews (of a record), most recent first. 404 `application_not_found` for an
    unknown record without interviews (an interview outlives its record)."""
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        rows = await InterviewRepository(db, user_id).recent(application_id)
        if application_id is not None and not rows:
            known = await ApplicationRepository(db, user_id).get(application_id)
            if known is None:
                raise not_found()
        return [interview_out(row) for row in rows]


async def get_interview(rt: ApplicationsRuntime, user_id: str, interview_id: str) -> InterviewOut:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return interview_out(await interview_row(db, user_id, interview_id))
