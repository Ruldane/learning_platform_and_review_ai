"""Explorateur de la mémoire (4.6, 14.2) : carte 2D, statistiques, réindexation, export JSON
(lien direct : `Content-Disposition: attachment`)."""

from fastapi import APIRouter, Response
from fastapi import status as http
from starlette.requests import HTTPConnection

from app.config import Settings
from app.core.deps import CurrentUserDep, Db
from app.features.memory.router.deps import MemoryRuntimeDep
from app.features.memory.schemas import MapResponse, MemoryExport, ReindexState, StatsOut
from app.features.memory.service.explorer import memory_export, memory_map, memory_stats

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/map", response_model=MapResponse)
async def get_map(current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep) -> MapResponse:
    return await memory_map(db, current.id, runtime)


@router.get("/stats", response_model=StatsOut)
async def get_stats(
    conn: HTTPConnection, current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep
) -> StatsOut:
    settings: Settings = conn.app.state.settings
    return await memory_stats(db, current.id, runtime, settings)


@router.post("/reindex", status_code=http.HTTP_202_ACCEPTED, response_model=ReindexState)
async def reindex(current: CurrentUserDep, runtime: MemoryRuntimeDep) -> ReindexState:
    """Met la réindexation en file (worker) ; déjà en file ou en cours : l'état courant."""
    return runtime.jobs.enqueue_reindex(current.id)


@router.get("/export", response_model=MemoryExport)
async def export(current: CurrentUserDep, db: Db, response: Response) -> MemoryExport:
    body = await memory_export(db, current.id)
    name = f"tremplin-memoire-{body.exported_at:%Y-%m-%d}.json"
    response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return body
