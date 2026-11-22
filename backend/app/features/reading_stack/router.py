from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.core.deps import CurrentUserDep, Db
from app.features.reading_stack.schemas import (
    ReadingDetail,
    ReadingKind,
    ReadingPage,
    ReadingSourceIn,
    ReadingSourceOut,
    ReadingSourceState,
    ReadState,
)
from app.features.reading_stack.service import entries, sources

router = APIRouter(prefix="/reading-stack", tags=["reading-stack"])


@router.get("", response_model=ReadingPage)
async def get_entries(
    current: CurrentUserDep,
    db: Db,
    unread: bool | None = None,
    kind: ReadingKind | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReadingPage:
    return await entries.list_entries(db, current.id, unread, kind, offset)


@router.get("/sources", response_model=list[ReadingSourceOut])
async def get_sources(current: CurrentUserDep, db: Db) -> list[ReadingSourceOut]:
    return await sources.list_sources(db, current.id)


@router.post("/sources", response_model=ReadingSourceOut, status_code=201)
async def create_source(body: ReadingSourceIn, current: CurrentUserDep, db: Db) -> ReadingSourceOut:
    return await sources.add_source(db, current.id, body)


@router.patch("/sources/{source_id}", response_model=ReadingSourceOut)
async def update_source(
    source_id: str, body: ReadingSourceState, current: CurrentUserDep, db: Db
) -> ReadingSourceOut:
    return await sources.set_active(db, current.id, source_id, body.active)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(source_id: str, current: CurrentUserDep, db: Db) -> Response:
    await sources.remove_source(db, current.id, source_id)
    return Response(status_code=204)


@router.get("/{item_id}", response_model=ReadingDetail)
async def get_entry(item_id: str, current: CurrentUserDep, db: Db) -> ReadingDetail:
    return ReadingDetail.model_validate(await entries.read_entry(db, current.id, item_id))


@router.patch("/{item_id}", response_model=ReadingDetail)
async def update_entry(
    item_id: str, body: ReadState, current: CurrentUserDep, db: Db
) -> ReadingDetail:
    return await entries.set_read(db, current.id, item_id, body.read)
