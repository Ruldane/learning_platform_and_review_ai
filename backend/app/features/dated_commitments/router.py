from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.dated_commitments import service
from app.features.dated_commitments.schemas import CommitmentCreate, CommitmentOut, CommitmentReview
from app.features.dated_commitments.service import CommitmentsRuntime

router = APIRouter(
    prefix="/dated-commitments", tags=["dated_commitments"], route_class=FieldPathsRoute
)


async def get_commitments(conn: HTTPConnection) -> CommitmentsRuntime:
    runtime: CommitmentsRuntime | None = getattr(conn.app.state, "dated_commitments", None)
    if runtime is None:
        runtime = CommitmentsRuntime(conn.app.state.session_factory)
        conn.app.state.dated_commitments = runtime
    return runtime


CommitmentsDep = Annotated[CommitmentsRuntime, Depends(get_commitments)]


@router.get("")
async def list_commitments(db: Db, user: CurrentUserDep) -> list[CommitmentOut]:
    return await service.list_commitments(db, user.id)


@router.get("/{commitment_id}")
async def read(commitment_id: UUID, db: Db, user: CurrentUserDep) -> CommitmentOut:
    return await service.read(db, user.id, str(commitment_id))


@router.post("", status_code=201)
async def create(
    action: CommitmentCreate, rt: CommitmentsDep, user: CurrentUserDep
) -> CommitmentOut:
    return await service.create(rt, user.id, action)


@router.post("/{commitment_id}/review")
async def review(
    commitment_id: UUID, action: CommitmentReview, rt: CommitmentsDep, user: CurrentUserDep
) -> CommitmentOut:
    return await service.review(rt, user.id, str(commitment_id), action)
