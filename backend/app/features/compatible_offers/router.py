from typing import Annotated

from fastapi import APIRouter, Depends, Path
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.compatible_offers.schemas import CompatibleOfferOut, CompatibleOfferPlan
from app.features.compatible_offers.service import get_offer, plan_offer
from app.features.gap.service import PlanGapIn
from app.features.replan.service.runtime import ReplanRuntime

router = APIRouter(
    prefix="/compatible-offers", tags=["compatible_offers"], route_class=FieldPathsRoute
)
RunId = Annotated[str, Path(min_length=1, max_length=36)]
Reference = Annotated[str, Path(pattern=r"^p[1-9][0-9]{0,2}$")]


def _replan(connection: HTTPConnection) -> ReplanRuntime:
    runtime: ReplanRuntime = connection.app.state.replan
    return runtime


ReplanDep = Annotated[ReplanRuntime, Depends(_replan)]


@router.get("/{run_id}/{ref}")
async def read_offer(
    run_id: RunId, ref: Reference, user: CurrentUserDep, db: Db
) -> CompatibleOfferOut:
    return await get_offer(db, user.id, run_id, ref)


@router.post("/{run_id}/{ref}/plan", status_code=202)
async def start_offer_plan(
    run_id: RunId, ref: Reference, body: PlanGapIn, user: CurrentUserDep, runtime: ReplanDep
) -> CompatibleOfferPlan:
    return await plan_offer(runtime, user.id, run_id, ref, body)
