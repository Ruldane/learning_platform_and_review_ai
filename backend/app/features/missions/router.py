from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.missions import service
from app.features.missions.schemas import MissionCreate, MissionOut, MissionProgress, MissionSubmit
from app.features.missions.service import MissionRuntime

router = APIRouter(prefix="/missions", tags=["missions"], route_class=FieldPathsRoute)


async def get_missions(conn: HTTPConnection) -> MissionRuntime:
    runtime: MissionRuntime | None = getattr(conn.app.state, "missions", None)
    if runtime is None:
        runtime = MissionRuntime(conn.app.state.session_factory)
        conn.app.state.missions = runtime
    return runtime


MissionsDep = Annotated[MissionRuntime, Depends(get_missions)]


@router.get("")
async def list_missions(rt: MissionsDep, user: CurrentUserDep) -> list[MissionOut]:
    return await service.list_missions(rt, user.id)


@router.get("/{mission_id}")
async def read_mission(mission_id: UUID, rt: MissionsDep, user: CurrentUserDep) -> MissionOut:
    return await service.read_mission(rt, user.id, str(mission_id))


@router.post("", status_code=201)
async def start_mission(action: MissionCreate, rt: MissionsDep, user: CurrentUserDep) -> MissionOut:
    return await service.start_mission(rt, user.id, action)


@router.patch("/{mission_id}/criteria/{index}")
async def update_criterion(
    mission_id: UUID,
    index: Annotated[int, Path(ge=0)],
    action: MissionProgress,
    rt: MissionsDep,
    user: CurrentUserDep,
) -> MissionOut:
    return await service.update_criterion(rt, user.id, str(mission_id), index, action)


@router.post("/{mission_id}/submission")
async def submit_mission(
    mission_id: UUID, action: MissionSubmit, rt: MissionsDep, user: CurrentUserDep
) -> MissionOut:
    return await service.submit_mission(rt, user.id, str(mission_id), action)
