"""Reserve the session and the submitted version in the same transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.boss_port import BOSS_GRAPH, BOSS_SUBJECT
from app.core.caller import Caller
from app.core.errors import AppError
from app.core.played import inherit_source
from app.db.base import new_id
from app.features.boss.challenge import ENTRY
from app.features.boss.repository import BossRepository
from app.features.boss.schemas import BossReviewStarted
from app.features.boss.service import Clock
from app.features.boss.service.diagnostic import job_for
from app.features.ide.service import IdeService
from app.features.sessions.service import session_facts


class _ExistingReview(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


async def launch_review(
    launcher: SessionLauncher, user_id: str, program_id: str, clock: Clock
) -> BossReviewStarted:
    async def prepare(db: AsyncSession, session_id: str) -> None:
        row = await BossRepository(db, user_id).require(program_id)
        if previous := row.review_session_id:
            facts = await session_facts(db, user_id, previous)
            if row.verdict is not None or (
                facts and facts.status in {"running", "paused", "waiting_user"}
            ):
                raise _ExistingReview(previous)
            # An interrupted evaluation resumes on the submission, even after the deadline.
            row.review_session_id = session_id
            return
        now = clock()
        if now >= row.deadline_at:
            raise AppError("boss_expired", "The challenge time is up.", 409)
        if now < row.change_at:
            raise AppError(
                "boss_change_pending", "Wait for the client to send the change request.", 409
            )
        project = await IdeService(db, user_id, None, Caller("app", "boss")).get_session(
            row.ide_session_id
        )
        if ENTRY not in project.files:
            raise AppError("boss_entry_missing", "The service.py file is required.", 422)
        run_id = new_id()
        job_for(run_id, project.files)
        row.submitted_at = now
        row.submitted_files = project.files
        row.sandbox_run_id = run_id
        row.review_session_id = session_id

    with inherit_source(user_id, None, "openai"):
        try:
            session = await launcher.start(
                user_id,
                BOSS_GRAPH,
                {"program_id": program_id},
                subject_type=BOSS_SUBJECT,
                subject_id=program_id,
                prepare=prepare,
            )
        except _ExistingReview as exc:
            session = exc.session_id
    return BossReviewStarted(session_id=session)
