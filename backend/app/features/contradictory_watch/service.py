from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.contradictory_watch import WatchExperiment
from app.features.contradictory_watch.repository import WatchRepository
from app.features.contradictory_watch.schemas import (
    WatchExperimentIn,
    WatchExperimentOut,
    WatchObservation,
)


def _view(row: WatchExperiment) -> WatchExperimentOut:
    return WatchExperimentOut.model_validate(
        {
            "id": row.id,
            "title": row.title,
            "sources": row.sources,
            "protocol": row.protocol,
            "criterion": row.criterion,
            "observation": row.observation,
            "status": "completed" if row.completed else "ready",
            "created_at": row.created_at,
        }
    )


async def create(db: AsyncSession, owner: str, request: WatchExperimentIn) -> WatchExperimentOut:
    row = await WatchRepository(db, owner).add(**request.model_dump(mode="json"))
    return _view(row)


async def history(db: AsyncSession, owner: str) -> list[WatchExperimentOut]:
    return [_view(row) for row in await WatchRepository(db, owner).recent()]


async def read(db: AsyncSession, owner: str, experiment_id: str) -> WatchExperimentOut:
    row = await WatchRepository(db, owner).get(experiment_id)
    if row is None:
        raise AppError("watch_not_found", "Experiment not found.", 404)
    return _view(row)


async def observe(
    db: AsyncSession, owner: str, experiment_id: str, observation: WatchObservation
) -> WatchExperimentOut:
    repo = WatchRepository(db, owner)
    await repo.begin_write()
    row = await repo.get(experiment_id)
    if row is None:
        raise AppError("watch_not_found", "Experiment not found.", 404)
    value = observation.model_dump(mode="json")
    if not row.completed:
        row.observation = value
        row.completed = True
        return _view(row)
    if row.observation == value:
        return _view(row)
    raise AppError("watch_already_observed", "This experiment already has a result.", 409)
