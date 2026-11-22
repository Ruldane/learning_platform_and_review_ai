from sqlalchemy import select

from app.db.models.portfolio import PortfolioDraft, PortfolioSite
from app.db.repository import UserScopedRepository


class Drafts(UserScopedRepository[PortfolioDraft]):
    model = PortfolioDraft


class Sites(UserScopedRepository[PortfolioSite]):
    model = PortfolioSite

    async def for_owner(self) -> PortfolioSite | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id)
        return await self.session.scalar(stmt)
