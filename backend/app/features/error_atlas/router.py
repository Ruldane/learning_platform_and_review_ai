from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.error_atlas import evidence, service
from app.features.error_atlas.schemas import (
    AtlasEvidenceOut,
    AtlasExerciseOut,
    AtlasHypothesisOut,
    AtlasObservationIn,
)
from app.features.error_atlas.service import AtlasRuntime

router = APIRouter(prefix="/error-atlas", tags=["error_atlas"], route_class=FieldPathsRoute)


async def get_atlas(conn: HTTPConnection) -> AtlasRuntime:
    runtime: AtlasRuntime | None = getattr(conn.app.state, "error_atlas", None)
    if runtime is None:
        runtime = AtlasRuntime(conn.app.state.session_factory)
        conn.app.state.error_atlas = runtime
    return runtime


AtlasDep = Annotated[AtlasRuntime, Depends(get_atlas)]


@router.get("")
async def list_hypotheses(db: Db, user: CurrentUserDep) -> list[AtlasHypothesisOut]:
    return await service.list_hypotheses(db, user.id)


@router.get("/evidence")
async def list_evidence(db: Db, user: CurrentUserDep) -> list[AtlasEvidenceOut]:
    return await evidence.list_evidence(db, user.id)


@router.post("/observations", status_code=201)
async def add_observation(
    rt: AtlasDep, user: CurrentUserDep, action: AtlasObservationIn
) -> AtlasHypothesisOut:
    return await service.observe(rt, user.id, action)


@router.post("/hypotheses/{hypothesis_id}/exercise", status_code=201)
async def start_exercise(
    rt: AtlasDep, user: CurrentUserDep, hypothesis_id: UUID
) -> AtlasExerciseOut:
    return await service.start_exercise(rt, user.id, str(hypothesis_id))
