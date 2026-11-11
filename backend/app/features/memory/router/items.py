"""Éléments de la mémoire et recherche (14.2). `since` et `until` bornent la date de création,
bornes incluses ; une date sans fuseau est lue en UTC."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi import status as http

from app.core.deps import CurrentUserDep, Db
from app.features.memory.router.deps import MemoryRuntimeDep
from app.features.memory.schemas import (
    ItemStatus,
    MemoryItemCreate,
    MemoryItemDetail,
    MemoryItemList,
    MemoryItemOut,
    MemoryItemPatch,
    MemoryKind,
    MergeRequest,
    SearchRequest,
    SearchResponse,
)
from app.features.memory.service.items import ItemFilter, MemoryService
from app.features.memory.service.merge import merge
from app.features.memory.service.search import search

router = APIRouter(prefix="/memory", tags=["memory"])


def _service(current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep) -> MemoryService:
    return MemoryService(db, current.id, runtime)


Service = Annotated[MemoryService, Depends(_service)]


def _utc(moment: datetime | None) -> datetime | None:
    return moment.replace(tzinfo=UTC) if moment is not None and moment.tzinfo is None else moment


@router.get("/items", response_model=MemoryItemList)
async def list_items(
    service: Service,
    kind: MemoryKind | None = None,
    tag: str | None = None,
    author: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    status: ItemStatus = "active",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemoryItemList:
    criteria = ItemFilter(
        kind=kind, tag=tag, author=author, since=_utc(since), until=_utc(until), status=status
    )
    return await service.list_items(criteria, limit=limit, offset=offset)


@router.post("/items", status_code=http.HTTP_201_CREATED, response_model=MemoryItemOut)
async def create_item(body: MemoryItemCreate, service: Service) -> MemoryItemOut:
    return await service.create_by_user(body)


@router.get("/items/{item_id}", response_model=MemoryItemDetail)
async def get_item(item_id: str, service: Service) -> MemoryItemDetail:
    return await service.detail(item_id)


@router.patch("/items/{item_id}", response_model=MemoryItemOut)
async def update_item(item_id: str, body: MemoryItemPatch, service: Service) -> MemoryItemOut:
    return await service.update(item_id, body)


@router.delete("/items/{item_id}", status_code=http.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str, service: Service) -> Response:
    await service.delete(item_id)
    return Response(status_code=http.HTTP_204_NO_CONTENT)


@router.post("/items/{item_id}/merge", response_model=MemoryItemOut)
async def merge_items(item_id: str, body: MergeRequest, service: Service) -> MemoryItemOut:
    """Fond `other_ids` dans l'élément (D67) : même type, ni document ni décision en attente."""
    return await merge(service, item_id, body.other_ids)


@router.post("/search", response_model=SearchResponse)
async def search_memory(
    body: SearchRequest, current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep
) -> SearchResponse:
    return await search(db, current.id, runtime, body)
