"""Réserver une étape à la fois et reprendre au dernier résultat rangé."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.recruitment_process_port import (
    RECRUITMENT_GRAPH,
    RecruitmentCriterion,
    RecruitmentKind,
)
from app.core.errors import AppError
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.recruitment_process import RecruitmentProcess
from app.features.recruitment_process.repository import RecruitmentCases
from app.features.recruitment_process.schemas import (
    RecruitmentChoice,
    RecruitmentMissingProof,
    RecruitmentOut,
    RecruitmentStarted,
    RecruitmentState,
    RecruitmentStep,
)
from app.features.sessions.service import session_facts


def stored_steps(row: RecruitmentProcess) -> list[RecruitmentStep]:
    return [RecruitmentStep.model_validate(item) for item in row.steps]


def active(steps: list[RecruitmentStep]) -> RecruitmentStep | None:
    return next((step for step in steps if step.grade is None), None)


async def _state(
    db: AsyncSession, user_id: str, current: RecruitmentStep | None
) -> RecruitmentState:
    if current is None:
        return "complete"
    if current.session_id is None:
        return "ready"
    session = await session_facts(db, user_id, current.session_id)
    return (
        "evaluating" if session is not None and session.status in OPEN_SESSION_STATES else "failed"
    )


async def view(db: AsyncSession, row: RecruitmentProcess) -> RecruitmentOut:
    steps = stored_steps(row)
    current = active(steps)
    return RecruitmentOut(
        id=row.id,
        posting_id=row.posting_id,
        posting_title=str(row.offer["title"]),
        company=row.offer["company"],
        created_at=row.created_at,
        project=RecruitmentChoice.model_validate(row.project) if row.project is not None else None,
        rubric=[RecruitmentCriterion.model_validate(criterion) for criterion in row.rubric],
        missing_proofs=[
            RecruitmentMissingProof.model_validate(item) for item in row.missing_proofs
        ],
        steps=steps,
        active_step=current.kind if current else None,
        state=await _state(db, row.user_id, current),
    )


async def read(db: AsyncSession, user_id: str, process_id: str) -> RecruitmentOut:
    return await view(db, await RecruitmentCases(db, user_id).require(process_id))


async def history(db: AsyncSession, user_id: str) -> list[RecruitmentOut]:
    return [await view(db, row) for row in await RecruitmentCases(db, user_id).history()]


async def submit(
    launcher: SessionLauncher, user_id: str, process_id: str, kind: RecruitmentKind, answer: str
) -> RecruitmentStarted:
    async def reserve(db: AsyncSession, session_id: str) -> None:
        row = await RecruitmentCases(db, user_id).require(process_id)
        steps = stored_steps(row)
        current = active(steps)
        if current is None or current.kind != kind:
            raise AppError("recruitment_wrong_step", "Termine d’abord l’étape ouverte.", 409)
        if await _state(db, user_id, current) == "evaluating":
            raise AppError("recruitment_busy", "Cette étape est déjà en évaluation.", 409)
        current.answer = answer
        current.session_id = session_id
        row.steps = [step.model_dump(mode="json") for step in steps]

    session_id = await launcher.start(
        user_id,
        RECRUITMENT_GRAPH,
        {"process_id": process_id},
        subject_type=RECRUITMENT_GRAPH,
        subject_id=process_id,
        prepare=reserve,
    )
    return RecruitmentStarted(session_id=session_id)
