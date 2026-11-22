from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.contradictory_watch import service
from app.features.contradictory_watch.schemas import (
    WatchExperimentIn,
    WatchExperimentOut,
    WatchObservation,
)

router = APIRouter(
    prefix="/contradictory-watch", tags=["contradictory_watch"], route_class=FieldPathsRoute
)


@router.get("")
async def list_experiments(db: Db, user: CurrentUserDep) -> list[WatchExperimentOut]:
    return await service.history(db, user.id)


@router.post("", status_code=201)
async def create_experiment(
    body: WatchExperimentIn, db: Db, user: CurrentUserDep
) -> WatchExperimentOut:
    return await service.create(db, user.id, body)


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: UUID, db: Db, user: CurrentUserDep) -> WatchExperimentOut:
    return await service.read(db, user.id, str(experiment_id))


@router.post("/{experiment_id}/observations")
async def record_observation(
    experiment_id: UUID, body: WatchObservation, db: Db, user: CurrentUserDep
) -> WatchExperimentOut:
    return await service.observe(db, user.id, str(experiment_id), body)
