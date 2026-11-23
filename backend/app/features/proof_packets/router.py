from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.missions.service import MissionRuntime
from app.features.proof_packets import service, sources
from app.features.proof_packets.schemas import (
    ProofPacketCreate,
    ProofPacketManifest,
    ProofPacketOut,
    ProofPacketPreview,
    ProofPacketSelection,
    ProofPacketSource,
    ProofPacketSummary,
)

_PRIVATE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


def _private(response: Response) -> None:
    response.headers.update(_PRIVATE)


router = APIRouter(
    prefix="/proof-packets",
    tags=["proof_packets"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(_private)],
)


def _missions(conn: HTTPConnection) -> MissionRuntime:
    return MissionRuntime(conn.app.state.session_factory)


Missions = Annotated[MissionRuntime, Depends(_missions)]


@router.get("/sources")
async def list_sources(user: CurrentUserDep, rt: Missions) -> list[ProofPacketSource]:
    return await sources.choices(rt, user.id)


@router.post("/preview")
async def preview_packet(
    body: ProofPacketSelection, user: CurrentUserDep, rt: Missions
) -> ProofPacketPreview:
    return await service.preview(rt, user.id, body)


@router.get("")
async def list_packets(user: CurrentUserDep, db: Db) -> list[ProofPacketSummary]:
    return await service.history(db, user.id)


@router.post("", status_code=201)
async def save_packet(
    body: ProofPacketCreate, user: CurrentUserDep, db: Db, rt: Missions
) -> ProofPacketOut:
    return await service.save(db, rt, user.id, body)


@router.get("/{packet_id}")
async def read_packet(packet_id: UUID, user: CurrentUserDep, db: Db) -> ProofPacketOut:
    return await service.read(db, user.id, str(packet_id))


@router.get("/{packet_id}/export", response_model=ProofPacketManifest)
async def export_packet(packet_id: UUID, user: CurrentUserDep, db: Db) -> Response:
    return Response(
        await service.export(db, user.id, str(packet_id)),
        media_type="application/json",
        headers={
            **_PRIVATE,
            "Content-Disposition": 'attachment; filename="dossier-de-preuves.json"',
        },
    )
