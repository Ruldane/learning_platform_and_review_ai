from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.interprogram_planning import service
from app.features.interprogram_planning.schemas import (
    SharedWeekAccept,
    SharedWeekCreate,
    SharedWeekOption,
    SharedWeekOut,
)
from app.features.interprogram_planning.service import SharedWeekRuntime

router = APIRouter(
    prefix="/interprogram-planning", tags=["interprogram_planning"], route_class=FieldPathsRoute
)


async def get_planning(conn: HTTPConnection) -> SharedWeekRuntime:
    runtime: SharedWeekRuntime | None = getattr(conn.app.state, "interprogram_planning", None)
    if runtime is None:
        runtime = SharedWeekRuntime(conn.app.state.program, conn.app.state.calendar)
        conn.app.state.interprogram_planning = runtime
    return runtime


PlanningDep = Annotated[SharedWeekRuntime, Depends(get_planning)]


@router.get("/options")
async def options(db: Db, user: CurrentUserDep) -> list[SharedWeekOption]:
    return await service.options(db, user.id)


@router.get("")
async def list_proposals(db: Db, user: CurrentUserDep) -> list[SharedWeekOut]:
    return await service.list_proposals(db, user.id)


@router.post("", status_code=201)
async def create(action: SharedWeekCreate, rt: PlanningDep, user: CurrentUserDep) -> SharedWeekOut:
    return await service.prepare(rt, user.id, action)


@router.post("/{proposal_id}/accept")
async def accept(
    proposal_id: UUID, action: SharedWeekAccept, rt: PlanningDep, user: CurrentUserDep
) -> SharedWeekOut:
    return await service.accept(rt, user.id, str(proposal_id))
