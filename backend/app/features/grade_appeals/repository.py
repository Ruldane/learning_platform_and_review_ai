from sqlalchemy import select

from app.core.errors import AppError
from app.db.models.grade_appeals import GradeAppeal
from app.db.repository import UserScopedRepository


class GradeAppeals(UserScopedRepository[GradeAppeal]):
    model = GradeAppeal

    async def require(self, appeal_id: str) -> GradeAppeal:
        row = await self.get(appeal_id)
        if row is None:
            raise AppError("grade_appeal_not_found", "Contestation de note introuvable.", 404)
        return row

    async def history(self) -> list[GradeAppeal]:
        query = (
            select(GradeAppeal)
            .where(GradeAppeal.user_id == self.user_id)
            .order_by(GradeAppeal.created_at.desc())
        )
        return list((await self.session.scalars(query)).all())
