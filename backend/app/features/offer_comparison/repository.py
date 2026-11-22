from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.db.base import new_id, utcnow
from app.db.models.offer_comparison import OfferComparisonPreference, OfferComparisonScenario
from app.db.repository import UserScopedRepository


class OfferPreferences(UserScopedRepository[OfferComparisonPreference]):
    model = OfferComparisonPreference

    async def preferences(self) -> dict[str, Any] | None:
        return await self.session.scalar(
            select(self.model.preferences).where(self.model.user_id == self.user_id)
        )

    async def replace(self, data: dict[str, Any]) -> None:
        now = utcnow()
        stmt = insert(self.model).values(
            id=new_id(), user_id=self.user_id, preferences=data, created_at=now, updated_at=now
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[self.model.user_id],
                set_={"preferences": data, "updated_at": now},
            )
        )


class OfferScenarios(UserScopedRepository[OfferComparisonScenario]):
    model = OfferComparisonScenario

    async def history(self) -> list[OfferComparisonScenario]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return list(await self.session.scalars(stmt))
