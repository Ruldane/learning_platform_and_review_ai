from sqlalchemy import select

from app.db.models.decision_lab import DecisionScenario
from app.db.repository import UserScopedRepository


class DecisionScenarioRepository(UserScopedRepository[DecisionScenario]):
    model = DecisionScenario

    async def history(self) -> list[DecisionScenario]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return list(await self.session.scalars(stmt))
