"""API de la replanification (SPEC F13, D106). Hors 14.2 : `POST /programs/{id}/replan` (message
de January, « cette semaine je n'ai que 5 heures ») et `GET /programs/{id}/versions`
(historique, 13.3). L'acceptation et le refus passent par la reprise de la session
(`POST /sessions/{id}/resume`, 14.1). Le programme d'un autre : 404."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.replan.schemas import PlanVersionOut, ReplanRequest, ReplanStarted
from app.features.replan.service import launch
from app.features.replan.service.runtime import ReplanRuntime

router = APIRouter(tags=["replan"])


def get_replan_runtime(conn: HTTPConnection) -> ReplanRuntime:
    """La replanification ouverte par le lifespan (`app.state.replan`)."""
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
    """Lance une replanification du Stratège. Brouillon : 409 `program_not_validated` ;
    replanification ouverte : 409 `replan_open` (`details.session_id`)."""
    return await launch.start_replan(rt, current.id, program_id, body)


@router.get("/programs/{program_id}/versions", response_model=list[PlanVersionOut])
async def list_versions(program_id: str, current: CurrentUserDep, db: Db) -> list[PlanVersionOut]:
    """Les versions du plan, la plus récente d'abord, avec leur statut."""
    return await launch.list_versions(db, current.id, program_id)
