"""API du radar du marché (SPEC 14.2, P10, D160) : lancer un relevé (202, le parcours tourne en
tâche de fond), le dernier relevé, la liste (20) et un relevé. Toutes au nom de l'utilisatrice
courante ; une 422 nomme les champs, sans jamais recopier le poste ni la zone."""

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
        "description": "`radar_in_progress` (`details.run_id`) ou `radar_role_required` : "
        "aucun poste ni dans la requête, ni dans les réglages, ni dans le dernier objectif"
    },
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "`radar_run_not_found`"}}


def get_radar_runtime(conn: HTTPConnection) -> RadarRuntime:
    """Le radar ouvert par le lifespan (`app.state.daily.radar`)."""
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
    """Lance un relevé. `role` et `zone` donnés sont mémorisés dans les réglages ; absents, ceux
    des réglages (poste : sinon celui du dernier objectif ; zone : « France »)."""
    return await start_run(rt, current.id, body or RadarRunIn(), trigger="manual", period=None)


@router.get("/latest", response_model=RadarLatestOut)
async def get_latest(current: CurrentUserDep, db: Db, rt: RadarDep) -> RadarLatestOut:
    """Le dernier relevé fini (réussi ou en échec), le relevé en cours s'il y en a un, et le poste
    et la zone proposés par défaut."""
    return await latest_out(rt, db, current.id)


@router.get("/runs", response_model=list[RadarRunSummary])
async def get_runs(current: CurrentUserDep, db: Db, rt: RadarDep) -> list[RadarRunSummary]:
    """Les 20 derniers relevés, le plus récent d'abord."""
    return await list_runs(rt, db, current.id)


@router.get("/runs/{run_id}", response_model=RadarRunOut, responses=_NOT_FOUND)
async def get_one_run(run_id: RunId, current: CurrentUserDep, db: Db, rt: RadarDep) -> RadarRunOut:
    return await get_run(rt, db, current.id, run_id)
