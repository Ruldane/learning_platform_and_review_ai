"""Les compétences qui manquent le plus souvent dans les offres de January (F8, D122) : lignes de
chaque offre recalculées comme `gap_rows`, contexte chargé une seule fois, puis `top_missing`. Les
lignes hors périmètre (permis, diplôme…) n'y entrent pas : aucun programme ne les comble."""

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
    ctx = await load_context(db, user_id)
    terms = await repo.review_terms([posting.id for posting in postings])
    rows = (rows_for(p, ctx, terms.get(p.id, [])) for p in postings)
    return top_missing(([r for r in found if r.action != "out_of_scope"] for found in rows), limit)
