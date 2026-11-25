"""Rating and simulation of demand in the account's observed market."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.skill_market.schemas import MarketQuery, SkillMarketOut
from app.features.skill_market.service import market

router = APIRouter(prefix="/skill-market", tags=["skill_market"], route_class=FieldPathsRoute)


@router.get("")
async def market_view(
    current: CurrentUserDep, db: Db, query: Annotated[MarketQuery, Query()]
) -> SkillMarketOut:
    return await market(db, current.id, query)
