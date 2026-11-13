"""API de l'écart (SPEC F8, D122) : le tableau d'une offre, recalculé à chaque lecture, et les
compétences qui manquent le plus souvent dans les offres de January."""

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.features.gap.schemas import GapOut, TopMissingOut
from app.features.gap.service.top import top_missing_skills
from app.features.gap.service.view import posting_gap

router = APIRouter(tags=["gap"])


@router.get("/postings/{posting_id}/gap", response_model=GapOut)
async def get_gap(posting_id: str, current: CurrentUserDep, db: Db) -> GapOut:
    """`pending` tant que l'analyse tourne ; offre d'une autre : 404 `posting_not_found`."""
    return await posting_gap(db, current.id, posting_id)


@router.get("/gap/top-missing", response_model=list[TopMissingOut])
async def get_top_missing(current: CurrentUserDep, db: Db) -> list[TopMissingOut]:
    """Les 10 compétences absentes demandées par le plus d'offres."""
    found = await top_missing_skills(db, current.id)
    return [
        TopMissingOut(skill=m.skill, postings=m.postings, required_in=m.required_in) for m in found
    ]
