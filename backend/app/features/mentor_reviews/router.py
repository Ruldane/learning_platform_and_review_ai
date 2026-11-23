from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db, InterfaceUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.mentor_reviews import service
from app.features.mentor_reviews.schemas import (
    MentorCommentCreate,
    MentorCommentOut,
    MentorCommentReview,
    MentorOwnedComment,
    MentorShareCreate,
    MentorShareDetail,
    MentorSharedWork,
    MentorShareIssued,
    MentorShareOut,
)


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


router = APIRouter(
    prefix="/mentor-reviews",
    tags=["mentor_reviews"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(_private)],
)
_bearer = HTTPBearer(auto_error=False, scheme_name="MentorAccess")


def _token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str:
    return credentials.credentials if credentials is not None else ""


MentorToken = Annotated[str, Depends(_token)]


@router.get("/shares")
async def list_shares(db: Db, user: CurrentUserDep) -> list[MentorShareOut]:
    return await service.list_owned(db, user.id)


@router.post("/shares", status_code=201)
async def issue_share(body: MentorShareCreate, db: Db, user: InterfaceUserDep) -> MentorShareIssued:
    return await service.create(db, user.id, body)


@router.get("/shares/{share_id}")
async def read_share(share_id: UUID, db: Db, user: CurrentUserDep) -> MentorShareDetail:
    return await service.read_owned(db, user.id, str(share_id))


@router.patch("/shares/{share_id}/comments/{comment_id}")
async def mark_comment(
    share_id: UUID, comment_id: UUID, body: MentorCommentReview, db: Db, user: CurrentUserDep
) -> MentorOwnedComment:
    return await service.mark_comment(db, user.id, str(share_id), str(comment_id), body.reviewed)


@router.delete("/shares/{share_id}", status_code=204)
async def revoke_share(share_id: UUID, db: Db, user: ConfirmedUserDep) -> None:
    await service.revoke(db, user.id, str(share_id))


@router.get("/shared")
async def shared_work(db: Db, token: MentorToken) -> MentorSharedWork:
    return await service.read_shared(db, token)


@router.post("/shared/comments", status_code=201)
async def write_comment(body: MentorCommentCreate, db: Db, token: MentorToken) -> MentorCommentOut:
    return await service.comment(db, token, body)
