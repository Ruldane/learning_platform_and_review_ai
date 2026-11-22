from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.memory.service.direct import schedule_indexing
from app.features.reading_stack.schemas import (
    CardsSaved,
    MemorySaved,
    PlanReadingIn,
    ReadingApplicationIn,
    ReadingApplicationSaved,
    ReadingCardIn,
    ReadingPlanStarted,
)
from app.features.reading_stack.service.actions import (
    ReadingActions,
    keep_memory,
    keep_offer,
    make_card,
    propose_reading,
)
from app.features.reading_stack.service.entries import read_entry

router = APIRouter(prefix="/reading-stack", tags=["reading-stack"])


def dependencies(conn: HTTPConnection) -> ReadingActions:
    state = conn.app.state
    return ReadingActions(state.memory, state.replan, state.career.applications)


ActionsDep = Annotated[ReadingActions, Depends(dependencies)]


@router.post("/{item_id}/memory", response_model=MemorySaved)
async def save_memory(
    item_id: str, current: CurrentUserDep, db: Db, actions: ActionsDep
) -> MemorySaved:
    row = await read_entry(db, current.id, item_id)
    memory_id = await keep_memory(actions, db, row)
    await db.commit()
    schedule_indexing(actions.memory, current.id)
    return MemorySaved(memory_item_id=memory_id)


@router.post("/{item_id}/cards", response_model=CardsSaved)
async def save_cards(
    item_id: str, current: CurrentUserDep, db: Db, body: ReadingCardIn | None = None
) -> CardsSaved:
    row = await read_entry(db, current.id, item_id)
    return CardsSaved(count=await make_card(db, row, passage=body.passage if body else None))


@router.post("/{item_id}/plan", response_model=ReadingPlanStarted, status_code=202)
async def start_plan(
    item_id: str, body: PlanReadingIn, current: CurrentUserDep, db: Db, actions: ActionsDep
) -> ReadingPlanStarted:
    row = await read_entry(db, current.id, item_id)
    return ReadingPlanStarted(session_id=await propose_reading(actions, row, body.program_id))


@router.post("/{item_id}/application", response_model=ReadingApplicationSaved, status_code=201)
async def save_application(
    item_id: str, body: ReadingApplicationIn, current: CurrentUserDep, db: Db, actions: ActionsDep
) -> ReadingApplicationSaved:
    row = await read_entry(db, current.id, item_id)
    return ReadingApplicationSaved(application_id=await keep_offer(actions, row, body))
