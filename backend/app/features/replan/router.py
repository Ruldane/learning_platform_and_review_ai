"""Replanning API (SPEC F13, D106). Outside 14.2: `POST /programs/{id}/replan` (January's
message, "this week I only have 5 hours") and `GET /programs/{id}/versions` (history, 13.3).
Acceptance and refusal go through resuming the session (`POST /sessions/{id}/resume`, 14.1).
Someone else's program: 404."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.replan.schemas import PlanVersionOut, ReplanRequest, ReplanStarted
from app.features.replan.service import launch
from app.features.replan.service.runtime import ReplanRuntime

router = APIRouter(tags=["replan"])


def get_replan_runtime(conn: HTTPConnection) -> ReplanRuntime:
    """The replanning runtime opened by the lifespan (`app.state.replan`)."""
    runtime: ReplanRuntime = conn.app.state.replan
    return runtime


ReplanDep = Annotated[ReplanRuntime, Depends(get_replan_runtime)]


@router.post(
    "/programs/{program_id}/replan",
    response_model=ReplanStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_replan(
    program_id: str, body: ReplanRequest, current: CurrentUserDep, rt: ReplanDep
) -> ReplanStarted:
    """Starts a Strategist replanning. Draft: 409 `program_not_validated`;
    replanning already open: 409 `replan_open` (`details.session_id`)."""
    return await launch.start_replan(rt, current.id, program_id, body)


@router.get("/programs/{program_id}/versions", response_model=list[PlanVersionOut])
async def list_versions(program_id: str, current: CurrentUserDep, db: Db) -> list[PlanVersionOut]:
    """The plan versions, most recent first, with their status."""
    return await launch.list_versions(db, current.id, program_id)
