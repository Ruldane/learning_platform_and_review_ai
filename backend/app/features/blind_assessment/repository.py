from sqlalchemy import select

from app.core.errors import AppError
from app.db.models.blind_assessment import BlindAssessment
from app.db.repository import UserScopedRepository


class BlindAssessments(UserScopedRepository[BlindAssessment]):
    model = BlindAssessment

    async def require(self, assessment_id: str) -> BlindAssessment:
        row = await self.get(assessment_id)
        if row is None:
            raise AppError("blind_assessment_not_found", "Blind assessment not found.", 404)
        return row

    async def recent(self) -> list[BlindAssessment]:
        query = (
            select(BlindAssessment)
            .where(BlindAssessment.user_id == self.user_id)
            .order_by(BlindAssessment.created_at.desc())
        )
        return list((await self.session.scalars(query)).all())
