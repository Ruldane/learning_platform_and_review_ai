"""Market radar API (SPEC 14.2, P10, D160): launch a run (202, the flow runs as a background
task), the latest run, the list (20) and a run. All on behalf of the current user; a 422 names
the fields, never copying the role or the zone back."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.radar.schemas import (
    RadarLatestOut,
    RadarRunIn,
    RadarRunOut,
    RadarRunSummary,
    RunStarted,
)
from app.features.radar.service.runs import start_run
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.views import get_run, latest_out, list_runs

router = APIRouter(prefix="/radar", tags=["radar"], route_class=FieldPathsRoute)

RunId = Annotated[str, Path(min_length=1, max_length=36)]
_START_ERRORS: dict[int | str, dict[str, Any]] = {
    409: {
        "description": "`radar_in_progress` (`details.run_id`) or `radar_role_required`: "
        "no role in the request, nor in the settings, nor in the last goal"
    },
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "`radar_run_not_found`"}}


def get_radar_runtime(conn: HTTPConnection) -> RadarRuntime:
    """The radar opened by the lifespan (`app.state.daily.radar`)."""
    runtime: RadarRuntime = conn.app.state.daily.radar
    return runtime


RadarDep = Annotated[RadarRuntime, Depends(get_radar_runtime)]


@router.post(
    "/runs",
    response_model=RunStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_START_ERRORS,
)
async def post_run(
    current: CurrentUserDep, rt: RadarDep, body: RadarRunIn | None = None
) -> RunStarted:
    """Launches a run. The given `role` and `zone` are saved in the settings; when absent, those
    of the settings (role: otherwise that of the last goal; zone: "France")."""
    return await start_run(rt, current.id, body or RadarRunIn(), trigger="manual", period=None)


@router.get("/latest", response_model=RadarLatestOut)
async def get_latest(current: CurrentUserDep, db: Db, rt: RadarDep) -> RadarLatestOut:
    """The last finished run (succeeded or failed), the run in progress if there is one, and the
    default role and zone."""
    return await latest_out(rt, db, current.id)


@router.get("/runs", response_model=list[RadarRunSummary])
async def get_runs(current: CurrentUserDep, db: Db, rt: RadarDep) -> list[RadarRunSummary]:
    """The last 20 runs, most recent first."""
    return await list_runs(rt, db, current.id)


@router.get("/runs/{run_id}", response_model=RadarRunOut, responses=_NOT_FOUND)
async def get_one_run(run_id: RunId, current: CurrentUserDep, db: Db, rt: RadarDep) -> RadarRunOut:
    return await get_run(rt, db, current.id, run_id)
