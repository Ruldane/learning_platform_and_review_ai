from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.offer_comparison.repository import OfferPreferences, OfferScenarios
from app.features.offer_comparison.schemas import (
    OfferComparisonHistoryItem,
    OfferComparisonPair,
    OfferComparisonPosting,
    OfferComparisonPreferences,
    OfferComparisonResult,
    OfferComparisonSaved,
)
from app.features.offer_comparison.scoring import OfferFacts, compare
from app.features.postings.service.queries import list_postings, read_posting


async def options(db: AsyncSession, user_id: str) -> list[OfferComparisonPosting]:
    return [
        OfferComparisonPosting(id=row.id, title=row.title, company=row.company)
        for row in await list_postings(db, user_id)
        if row.status == "ready"
    ]


async def get_preferences(db: AsyncSession, user_id: str) -> OfferComparisonPreferences:
    saved = await OfferPreferences(db, user_id).preferences()
    return OfferComparisonPreferences.model_validate(saved or {})


async def replace_preferences(
    db: AsyncSession, user_id: str, preferences: OfferComparisonPreferences
) -> OfferComparisonPreferences:
    await OfferPreferences(db, user_id).replace(preferences.model_dump(mode="json"))
    return preferences


async def _facts(db: AsyncSession, user_id: str, posting_id: str) -> OfferFacts:
    row = await read_posting(db, user_id, posting_id)
    if row.status != "ready":
        raise AppError("offer_comparison_pending", "Wait for the offer analysis to finish.", 409)
    return OfferFacts(
        id=row.id,
        title=row.title,
        company=row.company,
        match=row.score,
        remote=row.analysis.remote if row.analysis else None,
        location=row.analysis.location if row.analysis else None,
    )


async def preview(
    db: AsyncSession, user_id: str, body: OfferComparisonPair
) -> OfferComparisonResult:
    first = await _facts(db, user_id, str(body.first_id))
    second = await _facts(db, user_id, str(body.second_id))
    preferences = body.preferences or await get_preferences(db, user_id)
    return compare(first, second, preferences)


async def save(db: AsyncSession, user_id: str, body: OfferComparisonPair) -> OfferComparisonSaved:
    result = await preview(db, user_id, body)
    row = await OfferScenarios(db, user_id).add(result=result.model_dump(mode="json"))
    return OfferComparisonSaved(id=row.id, created_at=row.created_at, result=result)


async def read(db: AsyncSession, user_id: str, scenario_id: str) -> OfferComparisonSaved:
    row = await OfferScenarios(db, user_id).get(scenario_id)
    if row is None:
        raise AppError("offer_comparison_not_found", "Offer comparison not found.", 404)
    return OfferComparisonSaved.model_validate(row, from_attributes=True)


async def history(db: AsyncSession, user_id: str) -> list[OfferComparisonHistoryItem]:
    rows = await OfferScenarios(db, user_id).history()
    return [
        OfferComparisonHistoryItem(
            id=row.id,
            created_at=row.created_at,
            first=OfferComparisonPosting.model_validate(row.result["first"]),
            second=OfferComparisonPosting.model_validate(row.result["second"]),
        )
        for row in rows
    ]
