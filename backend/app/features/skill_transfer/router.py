"""Contrôles privés, réponses réservées au compte dans l’application."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.core.caller import JanuaryOnly
from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.skill_transfer.schemas import (
    AnswerIn,
    ProofOption,
    TransferIn,
    TransferOut,
    TransferStarted,
)
from app.features.skill_transfer.service import transfers

router = APIRouter(prefix="/skill-transfers", tags=["skill_transfer"], route_class=FieldPathsRoute)


def clock() -> datetime:
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(clock)]


@router.get("/proofs")
async def list_proofs(
    db: Db, current: CurrentUserDep, response: Response, skill_id: UUID | None = None
) -> list[ProofOption]:
    response.headers["Cache-Control"] = "no-store"
    return await transfers.proofs(db, current.id, str(skill_id) if skill_id else None)


@router.get("")
async def list_transfers(
    db: Db, current: CurrentUserDep, response: Response, now: Now, skill_id: UUID | None = None
) -> list[TransferOut]:
    response.headers["Cache-Control"] = "no-store"
    return await transfers.history(db, current.id, str(skill_id) if skill_id else None, now)


@router.post("", status_code=201)
async def create_transfer(
    body: TransferIn, db: Db, current: CurrentUserDep, now: Now
) -> TransferOut:
    return await transfers.schedule(db, current.id, body, now)


@router.get("/{transfer_id}")
async def read_transfer(
    transfer_id: UUID, db: Db, current: CurrentUserDep, response: Response, now: Now
) -> TransferOut:
    response.headers["Cache-Control"] = "no-store"
    return await transfers.read(db, current.id, str(transfer_id), now)


@router.post("/{transfer_id}/prepare", status_code=202, dependencies=[JanuaryOnly])
async def prepare_transfer(
    transfer_id: UUID, request: Request, current: CurrentUserDep, now: Now
) -> TransferStarted:
    return await transfers.launch(request.app.state.launcher, current.id, str(transfer_id), now)


@router.post("/{transfer_id}/answer", status_code=202, dependencies=[JanuaryOnly])
async def answer_transfer(
    transfer_id: UUID, body: AnswerIn, request: Request, current: CurrentUserDep, now: Now
) -> TransferStarted:
    return await transfers.launch(
        request.app.state.launcher, current.id, str(transfer_id), now, body
    )
