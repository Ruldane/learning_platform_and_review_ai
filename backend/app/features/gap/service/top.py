"""Les compétences apprenables qui manquent le plus souvent dans les offres (F8, D122)."""

from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.gap.repository import GapRepository
from app.features.gap.service.rows import load_context, rows_for
from app.features.gap.service.score import TOP_MISSING, MissingSkill, top_missing


async def top_missing_skills(
    db: AsyncSession, user_id: str, limit: int = TOP_MISSING
) -> list[MissingSkill]:
    repo = GapRepository(db, user_id)
    postings = await repo.with_gap()
    if not postings:
        return []
    ctx = replace(await load_context(db, user_id), offer_weeks={})
    terms = await repo.review_terms([posting.id for posting in postings])
    rows = (rows_for(p, ctx, terms.get(p.id, [])) for p in postings)
    return top_missing(([r for r in found if r.action != "out_of_scope"] for found in rows), limit)
