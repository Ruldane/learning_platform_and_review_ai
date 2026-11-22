from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.features.routines import service
from app.features.routines.schemas import (
    ExecutionIn,
    ExecutionOut,
    RoutineIn,
    RoutineOut,
    RoutinePatch,
)

router = APIRouter(prefix="/routines", tags=["routines"])


@router.get("")
async def list_routines(current: CurrentUserDep, db: Db) -> list[RoutineOut]:
    return [RoutineOut.model_validate(row) for row in await service.list_rules(db, current.id)]


@router.post("", status_code=201)
async def create_routine(body: RoutineIn, current: CurrentUserDep, db: Db) -> RoutineOut:
    return RoutineOut.model_validate(await service.create(db, current.id, body, datetime.now(UTC)))


@router.patch("/{routine_id}")
async def update_routine(
    routine_id: UUID, body: RoutinePatch, current: CurrentUserDep, db: Db
) -> RoutineOut:
    row = await service.change(db, current.id, str(routine_id), body, datetime.now(UTC))
    return RoutineOut.model_validate(row)


@router.get("/{routine_id}/executions")
async def list_executions(routine_id: UUID, current: CurrentUserDep, db: Db) -> list[ExecutionOut]:
    rows = await service.history(db, current.id, str(routine_id))
    return [ExecutionOut.model_validate(row) for row in rows]


@router.post("/{routine_id}/executions", status_code=201)
async def execute_routine(
    routine_id: UUID, body: ExecutionIn, current: CurrentUserDep, db: Db
) -> ExecutionOut:
    row = await service.execute_now(
        db, current.id, str(routine_id), str(body.receipt), datetime.now(UTC)
    )
    return ExecutionOut.model_validate(row)
