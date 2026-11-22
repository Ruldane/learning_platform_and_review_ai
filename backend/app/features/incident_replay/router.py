from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.incident_replay import service
from app.features.incident_replay.schemas import (
    IncidentNote,
    IncidentReplayIn,
    IncidentReplayOut,
    IncidentScenarioOut,
)

router = APIRouter(
    prefix="/incident-replays", tags=["incident_replay"], route_class=FieldPathsRoute
)


@router.get("/scenarios")
async def list_scenarios(user: CurrentUserDep) -> list[IncidentScenarioOut]:
    return service.catalog()


@router.get("")
async def list_replays(db: Db, user: CurrentUserDep) -> list[IncidentReplayOut]:
    return [IncidentReplayOut.model_validate(row) for row in await service.history(db, user.id)]


@router.post("", status_code=201)
async def create_replay(body: IncidentReplayIn, db: Db, user: CurrentUserDep) -> IncidentReplayOut:
    return IncidentReplayOut.model_validate(await service.create(db, user.id, body))


@router.get("/{replay_id}")
async def read_replay(replay_id: UUID, db: Db, user: CurrentUserDep) -> IncidentReplayOut:
    return IncidentReplayOut.model_validate(await service.read(db, user.id, str(replay_id)))


@router.post("/{replay_id}/notes")
async def annotate_replay(
    replay_id: UUID, body: IncidentNote, db: Db, user: CurrentUserDep
) -> IncidentReplayOut:
    return IncidentReplayOut.model_validate(
        await service.annotate(db, user.id, str(replay_id), body)
    )
