"""Réserve l’entretien technique et sa session dans la transaction du lancement."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.applications.repository_interviews import InterviewRepository
from app.features.applications.schemas_interviews import InterviewOut, InterviewStartOut
from app.features.applications.service.interviews import (
    GRAPH,
    SUBJECT,
    interview_lock,
    interview_out,
    require_interview_available,
)
from app.features.applications.service.runtime import ApplicationsRuntime


async def read_telegram_interview(
    db: AsyncSession, user_id: str, invitation_id: str
) -> InterviewOut | None:
    row = await InterviewRepository(db, user_id).get_fresh(invitation_id)
    if row is None or row.surprise_invitation_id != invitation_id:
        return None
    return interview_out(row)


async def start_telegram_interview(
    rt: ApplicationsRuntime,
    user_id: str,
    invitation_id: str,
    role: str,
    check: Callable[[AsyncSession], Awaitable[None]],
) -> InterviewStartOut:
    async with interview_lock(rt, user_id):
        async with rt.session_factory() as db:
            existing = await InterviewRepository(db, user_id).get_fresh(invitation_id)
            if existing is not None and existing.surprise_invitation_id == invitation_id:
                return InterviewStartOut(interview_id=existing.id, session_id=existing.session_id)
            await require_interview_available(db, user_id)

        async def prepare(db: AsyncSession, session_id: str) -> None:
            await check(db)
            await InterviewRepository(db, user_id).add(
                id=invitation_id,
                surprise_invitation_id=invitation_id,
                role=role,
                mode="technical",
                duration_min=15,
                language="en",
                session_id=session_id,
                status="running",
            )

        session_id = await rt.launcher.start(
            user_id,
            GRAPH,
            {"interview_id": invitation_id},
            subject_type=SUBJECT,
            subject_id=invitation_id,
            prepare=prepare,
        )
        return InterviewStartOut(interview_id=invitation_id, session_id=session_id)
