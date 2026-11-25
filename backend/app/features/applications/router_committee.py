"""Simulated hiring committee API (SPEC F19, D147): starts the `hiring_committee` flow on a ready
CV version, list and detail (votes, verdict, objections, changes, before and after). All on
behalf of the current user; a 422 names the fields, never quoting the input. The screen says it
is a simulation, never a prediction."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.applications.router import ApplicationsDep, Id
from app.features.applications.schemas_committee import (
    CommitteeIn,
    CommitteeRunOut,
    CommitteeStartOut,
)
from app.features.applications.service.committee import get_run, list_runs, start_committee

router = APIRouter(prefix="/committee", tags=["committee"], route_class=FieldPathsRoute)

_START: dict[int | str, dict[str, Any]] = {
    404: {"description": "`version_not_found`, `posting_not_found`"},
    409: {
        "description": (
            "`version_not_ready` (the version's PDF is not rendered), "
            "`committee_in_progress` (`details.run_id`: the posting's open run), "
            "`profile_required` (no validated master profile)"
        )
    },
    503: {"description": "`engine_unavailable`"},
}


@router.post("", response_model=CommitteeStartOut, status_code=202, responses=_START)
async def post_committee(
    body: CommitteeIn, current: CurrentUserDep, rt: ApplicationsDep
) -> CommitteeStartOut:
    """Convenes the committee on the CV version: impressions, two debate rounds, votes and
    synthesis arrive through the session events; the result is stored at the end."""
    return await start_committee(rt, current.id, body)


@router.get("", response_model=list[CommitteeRunOut])
async def get_committees(
    current: CurrentUserDep,
    rt: ApplicationsDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[CommitteeRunOut]:
    """The runs (of a posting), most recent first, each with its before and after; a run whose
    session ended without a result turns `failed`."""
    return await list_runs(rt, current.id, posting_id)


@router.get(
    "/{run_id}",
    response_model=CommitteeRunOut,
    responses={404: {"description": "`committee_not_found`"}},
)
async def get_committee(
    run_id: Id, current: CurrentUserDep, rt: ApplicationsDep
) -> CommitteeRunOut:
    return await get_run(rt, current.id, run_id)
