from sqlalchemy import select, update

from app.db.models.learning import DesignBoardVersion
from app.db.repository import UserScopedRepository


class DesignBoards(UserScopedRepository[DesignBoardVersion]):
    model = DesignBoardVersion

    async def latest(self, interview_id: str) -> DesignBoardVersion | None:
        stmt = (
            select(self.model)
            .where(self.model.user_id == self.user_id, self.model.interview_id == interview_id)
            .order_by(self.model.step.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def lock(self, board_id: str) -> DesignBoardVersion | None:
        stmt = (
            update(self.model)
            .where(self.model.user_id == self.user_id, self.model.id == board_id)
            .values(updated_at=self.model.updated_at)
            .returning(self.model)
        )
        return await self.session.scalar(stmt)
