from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.meeting_modules import service
from app.features.meeting_modules.schemas import (
    MeetingModuleIn,
    MeetingModuleOut,
    MeetingModuleSummary,
    MeetingSelection,
)

router = APIRouter(prefix="/meeting-modules", tags=["meeting_modules"], route_class=FieldPathsRoute)


@router.get("")
async def list_modules(db: Db, user: CurrentUserDep) -> list[MeetingModuleSummary]:
    return await service.history(db, user.id)


@router.post("", status_code=201)
async def prepare_module(body: MeetingModuleIn, db: Db, user: CurrentUserDep) -> MeetingModuleOut:
    return await service.prepare(db, user.id, body)


@router.get("/{module_id}")
async def read_module(module_id: UUID, db: Db, user: CurrentUserDep) -> MeetingModuleOut:
    return await service.read(db, user.id, str(module_id))


@router.put("/{module_id}/selection")
async def change_selection(
    module_id: UUID, body: MeetingSelection, db: Db, user: CurrentUserDep
) -> MeetingModuleOut:
    return await service.choose(db, user.id, str(module_id), body)


@router.post("/{module_id}/publish")
async def publish_module(
    module_id: UUID, body: MeetingSelection, db: Db, user: CurrentUserDep
) -> MeetingModuleOut:
    return await service.publish(db, user.id, str(module_id), body)
