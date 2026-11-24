"""Open the board, submit the selected version and store the review."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.repositories import SessionRepository
from app.agents.tools.system_design_port import (
    SystemDesignContext,
    SystemDesignReview,
    SystemDesignSubmission,
)
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.base import new_id
from app.db.models.applications import Interview
from app.features.applications.repository_interviews import InterviewRepository
from app.features.applications.schemas_interviews import InterviewStartOut
from app.features.applications.schemas_system_design import DesignState, DesignSubject
from app.features.applications.service.design_scene import describe_scene
from app.features.applications.service.interviews import GRAPH, SUBJECT, interview_lock, settle
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.learning.service.design_boards import create_design_board, read_design_board
from app.features.skills.service import SkillsService

SKILL = "System design"
LEGACY_SKILL = "Conception de systèmes"
SUBJECT_CARD = DesignSubject(
    title="Design a reminder service",
    situation="Teams schedule reminders for their members. Traffic peaks at the start of the day.",
    requirements=(
        "Schedule and cancel reminders before delivery.",
        "Handle 10,000 reminders due within the same minute.",
        "Resume deliveries after an outage and limit duplicates.",
        "Explain the trade-off between cost, latency and reliability.",
    ),
)


def _missing() -> AppError:
    return AppError("design_not_found", "System design interview not found.", 404)


async def _row(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
    row = await InterviewRepository(db, user_id).get_fresh(interview_id)
    if row is None or row.system_design is None:
        raise _missing()
    return row


async def start(rt: ApplicationsRuntime, user_id: str) -> InterviewStartOut:
    async with interview_lock(rt, user_id):
        async with rt.session_factory() as db:
            await settle(db, user_id)
            existing = await InterviewRepository(db, user_id).recent_design()
            if existing is not None and existing.status == "running":
                return InterviewStartOut(interview_id=existing.id, session_id=existing.session_id)

        interview_id = new_id()

        async def prepare(db: AsyncSession, session_id: str) -> None:
            await InterviewRepository(db, user_id).add(
                id=interview_id,
                session_id=session_id,
                role=SUBJECT_CARD.title,
                mode="case",
                duration_min=30,
                language="en",
                status="running",
                system_design={"subject": SUBJECT_CARD.model_dump(mode="json")},
            )
            await create_design_board(db, user_id, interview_id, session_id)

        session_id = await rt.launcher.start(
            user_id,
            GRAPH,
            {"interview_id": interview_id, "system_design": True},
            subject_type=SUBJECT,
            subject_id=interview_id,
            prepare=prepare,
        )
        return InterviewStartOut(interview_id=interview_id, session_id=session_id)


async def _view(db: AsyncSession, user_id: str, row: Interview) -> DesignState:
    data = row.system_design or {}
    version_id = data.get("version_id")
    board = await read_design_board(db, user_id, row.id, version_id)
    return DesignState.model_validate(
        {
            "id": row.id,
            "session_id": row.session_id,
            "status": row.status,
            "subject": data["subject"],
            "board": board,
            "version_id": version_id,
            "defense": data.get("defense"),
            "review": data.get("review"),
            "proof_saved": data.get("proof_saved", False),
        }
    )


async def read(
    rt: ApplicationsRuntime, user_id: str, interview_id: str | None = None
) -> DesignState | None:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = (
            await _row(db, user_id, interview_id)
            if interview_id is not None
            else await InterviewRepository(db, user_id).recent_design()
        )
        return await _view(db, user_id, row) if row is not None else None


async def _session_row(
    db: AsyncSession, user_id: str, interview_id: str, session_id: str
) -> Interview:
    row = await _row(db, user_id, interview_id)
    if row.session_id != session_id:
        raise _missing()
    return row


async def freeze(
    rt: ApplicationsRuntime,
    user_id: str,
    session_id: str,
    interview_id: str,
    submission: SystemDesignSubmission,
) -> SystemDesignContext:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        row = await _session_row(db, user_id, interview_id, session_id)
        if row.status != "running":
            raise AppError("design_closed", "This system design interview has ended.", 409)
        data: dict[str, Any] = dict(row.system_design or {})
        version_id = data.get("version_id") or str(submission.board_id)
        defense = data.get("defense") or submission.defense
        board = await read_design_board(db, user_id, interview_id, version_id)
        diagram = describe_scene(board.scene)
        if "version_id" not in data:
            row.system_design = {**data, "version_id": version_id, "defense": defense}
            await db.commit()
        subject = DesignSubject.model_validate(data["subject"])
        return SystemDesignContext(
            subject.title, subject.situation, subject.requirements, diagram, defense
        )


async def _record_proof(db: AsyncSession, rt: ApplicationsRuntime, row: Interview) -> None:
    skills = SkillsService(db, row.user_id)
    name = SKILL
    if await skills.skill_id_for(SKILL) is None and await skills.skill_id_for(LEGACY_SKILL):
        name = LEGACY_SKILL
    proof = evidence("system_design", row.id, "Passed system design interview", rt.now())
    await skills.raise_levels([name], "en_cours", proof)


async def save_review(
    rt: ApplicationsRuntime,
    user_id: str,
    session_id: str,
    interview_id: str,
    review: SystemDesignReview,
) -> None:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        # Acquire the SQLite write lock before reading the interview so cancellation
        # can prevent the review and its evidence from being stored.
        if not await SessionRepository(db, user_id).transition(
            session_id, from_={"running"}, to="running"
        ):
            return
        row = await _session_row(db, user_id, interview_id, session_id)
        if row.status != "running":
            return
        data = row.system_design or {}
        if "version_id" not in data:
            raise AppError("design_missing_submission", "Submitted diagram version not found.", 409)
        proof_saved = review.earns_proof
        if proof_saved:
            await _record_proof(db, rt, row)
        row.status = "done"
        row.system_design = {
            **data,
            "review": review.model_dump(mode="json"),
            "proof_saved": proof_saved,
        }
        await db.commit()
