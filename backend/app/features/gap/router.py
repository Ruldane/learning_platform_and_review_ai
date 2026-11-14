"""API de l'écart (SPEC F8, D122, D123) : le tableau d'une offre, recalculé à chaque lecture, les
compétences qui manquent le plus souvent dans les offres de January et « Ajouter au planning »
(une replanification au déclencheur `gap`, validée par January)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.gap.schemas import GapOut, PlanGapIn, PlanGapStarted, TopMissingOut
from app.features.gap.service.plan import plan_gap
from app.features.gap.service.top import top_missing_skills
from app.features.gap.service.view import posting_gap
from app.features.replan.service.runtime import ReplanRuntime

router = APIRouter(tags=["gap"])


def get_replan_runtime(conn: HTTPConnection) -> ReplanRuntime:
    """La replanification ouverte par le lifespan (`app.state.replan`)."""
    runtime: ReplanRuntime = conn.app.state.replan
    return runtime


ReplanDep = Annotated[ReplanRuntime, Depends(get_replan_runtime)]


@router.get("/postings/{posting_id}/gap", response_model=GapOut)
async def get_gap(posting_id: str, current: CurrentUserDep, db: Db) -> GapOut:
    """`pending` tant que l'analyse tourne ; offre d'une autre : 404 `posting_not_found`."""
    return await posting_gap(db, current.id, posting_id)


@router.post(
    "/postings/{posting_id}/gap/plan",
    response_model=PlanGapStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_gap_plan(
    posting_id: str, body: PlanGapIn, current: CurrentUserDep, rt: ReplanDep
) -> PlanGapStarted:
    """« Ajouter au planning » : lance une replanification du programme validé le plus récent,
    ajouts seuls (module « Compétences des offres »), proposée à January avant toute écriture.
    422 `gap_skill_unknown` (`details.fields` : `skills.{rang}`, sans valeur) si une compétence
    n'est pas une ligne `to_add` de l'écart ; 409 `no_program` ; 409 `replan_open`
    (`details.session_id`) si une replanification est déjà ouverte."""
    session_id = await plan_gap(rt, current.id, posting_id, body.skills)
    return PlanGapStarted(session_id=session_id)


@router.get("/gap/top-missing", response_model=list[TopMissingOut])
async def get_top_missing(current: CurrentUserDep, db: Db) -> list[TopMissingOut]:
    """Les 10 compétences absentes demandées par le plus d'offres."""
    found = await top_missing_skills(db, current.id)
    return [
        TopMissingOut(skill=m.skill, postings=m.postings, required_in=m.required_in) for m in found
    ]
