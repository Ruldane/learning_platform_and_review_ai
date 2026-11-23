from uuid import UUID

from fastapi import APIRouter

from app.core.caller import ConfirmedGesture
from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.offer_comparison import service
from app.features.offer_comparison.schemas import (
    OfferComparisonHistoryItem,
    OfferComparisonPair,
    OfferComparisonPosting,
    OfferComparisonPreferences,
    OfferComparisonResult,
    OfferComparisonSaved,
)

router = APIRouter(
    prefix="/offer-comparisons", tags=["offer_comparison"], route_class=FieldPathsRoute
)


@router.get("/postings")
async def list_comparable_postings(db: Db, user: CurrentUserDep) -> list[OfferComparisonPosting]:
    return await service.options(db, user.id)


@router.get("/preferences")
async def get_offer_comparison_preferences(
    db: Db, user: CurrentUserDep
) -> OfferComparisonPreferences:
    return await service.get_preferences(db, user.id)


@router.put("/preferences", dependencies=[ConfirmedGesture])
async def put_offer_comparison_preferences(
    body: OfferComparisonPreferences, db: Db, user: CurrentUserDep
) -> OfferComparisonPreferences:
    return await service.replace_preferences(db, user.id, body)


@router.post("/preview")
async def preview_offer_comparison(
    body: OfferComparisonPair, db: Db, user: CurrentUserDep
) -> OfferComparisonResult:
    return await service.preview(db, user.id, body)


@router.post("", status_code=201)
async def save_offer_comparison(
    body: OfferComparisonPair, db: Db, user: CurrentUserDep
) -> OfferComparisonSaved:
    return await service.save(db, user.id, body)


@router.get("")
async def list_offer_comparisons(db: Db, user: CurrentUserDep) -> list[OfferComparisonHistoryItem]:
    return await service.history(db, user.id)


@router.get("/{scenario_id}")
async def read_offer_comparison(
    scenario_id: UUID, db: Db, user: CurrentUserDep
) -> OfferComparisonSaved:
    return await service.read(db, user.id, str(scenario_id))
