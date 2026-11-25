"""Verifier port, reading only the neutralised texts."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.blind_assessment_port import BlindContext, BlindGrade
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.blind_assessment import BlindAssessment
from app.features.blind_assessment.repository import BlindAssessments
from app.features.blind_assessment.schemas import BlindRubric


async def _bound(
    db: AsyncSession, user_id: str, assessment_id: str, session_id: str
) -> BlindAssessment:
    row = await BlindAssessments(db, user_id).require(assessment_id)
    if row.session_id != session_id:
        raise AppError("blind_evaluation_changed", "This evaluation is no longer active.", 409)
    return row


class AgentBlindAssessmentStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, assessment_id: str, session_id: str) -> BlindContext:
        async with self._factory() as db:
            row = await _bound(db, user_id, assessment_id, session_id)
            return BlindContext(
                text_a=str(row.source_a["text"]),
                text_b=str(row.source_b["text"]),
                criteria=BlindRubric.model_validate(row.rubric).criteria,
                complete=row.stage == "complete",
            )

    async def finish(
        self, user_id: str, assessment_id: str, session_id: str, grade: BlindGrade
    ) -> None:
        async with self._factory.begin() as db:
            row = await _bound(db, user_id, assessment_id, session_id)
            if row.stage == "evaluating":
                row.grade = grade.model_dump()
                row.evaluated_at = utcnow()
                row.stage = "complete"
