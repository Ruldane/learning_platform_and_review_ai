"""Lancer une relecture et conserver la décision explicite sans réécrire la première note."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.grade_appeals_port import APPEAL_GRAPH, AppealReading
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.grade_appeals import AppealDecision, GradeAppeal
from app.features.grade_appeals.repository import GradeAppeals
from app.features.grade_appeals.schemas import (
    AppealState,
    GradeAppealOut,
    GradeAppealSource,
    GradeAppealStarted,
)
from app.features.sessions.service import session_facts


async def _state(db: AsyncSession, row: GradeAppeal) -> AppealState:
    if row.decision is not None:
        return "decided"
    if row.second is not None:
        return "ready"
    if row.session_id is None:
        return "draft"
    session = await session_facts(db, row.user_id, row.session_id)
    return (
        "reviewing" if session is not None and session.status in OPEN_SESSION_STATES else "failed"
    )


async def view(db: AsyncSession, row: GradeAppeal) -> GradeAppealOut:
    return GradeAppealOut(
        id=row.id,
        created_at=row.created_at,
        source=GradeAppealSource.model_validate(row.source),
        reason=row.reason,
        state=await _state(db, row),
        second=AppealReading.model_validate(row.second) if row.second is not None else None,
        reviewed_at=row.reviewed_at,
        decision=row.decision,
        decided_at=row.decided_at,
    )


async def read(db: AsyncSession, user_id: str, appeal_id: str) -> GradeAppealOut:
    return await view(db, await GradeAppeals(db, user_id).require(appeal_id))


async def history(db: AsyncSession, user_id: str) -> list[GradeAppealOut]:
    return [await view(db, row) for row in await GradeAppeals(db, user_id).history()]


async def review(launcher: SessionLauncher, user_id: str, appeal_id: str) -> GradeAppealStarted:
    async def reserve(db: AsyncSession, session_id: str) -> None:
        row = await GradeAppeals(db, user_id).require(appeal_id)
        if await _state(db, row) not in {"draft", "failed"}:
            raise AppError("grade_appeal_review_started", "La relecture est déjà lancée.", 409)
        row.session_id = session_id

    session_id = await launcher.start(
        user_id,
        APPEAL_GRAPH,
        {"appeal_id": appeal_id},
        subject_type=APPEAL_GRAPH,
        subject_id=appeal_id,
        prepare=reserve,
    )
    return GradeAppealStarted(session_id=session_id)


async def decide(
    db: AsyncSession, user_id: str, appeal_id: str, decision: AppealDecision
) -> GradeAppealOut:
    await db.execute(text("BEGIN IMMEDIATE"))
    row = await GradeAppeals(db, user_id).require(appeal_id)
    if row.second is None:
        raise AppError("grade_appeal_review_pending", "Attends la seconde lecture.", 409)
    if row.decision is not None and row.decision != decision:
        raise AppError("grade_appeal_decided", "Une décision définitive est déjà enregistrée.", 409)
    if row.decision is None:
        row.decision = decision
        row.decided_at = utcnow()
    return await view(db, row)
