from typing import Annotated

from fastapi import APIRouter, Depends, Path
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db, InterfaceUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.cv.service.runtime import CvRuntime
from app.features.linkedin_drafts.schemas import LinkedInDraftOut, LinkedInEdit, LinkedInStart
from app.features.linkedin_drafts.service import actions

router = APIRouter(prefix="/linkedin-drafts", tags=["linkedin_drafts"], route_class=FieldPathsRoute)
DraftId = Annotated[str, Path(min_length=36, max_length=36)]


def _runtime(conn: HTTPConnection) -> CvRuntime:
    runtime: CvRuntime = conn.app.state.career.cv
    return runtime


Runtime = Annotated[CvRuntime, Depends(_runtime)]


@router.get("/latest")
async def get_latest(current: CurrentUserDep, db: Db) -> LinkedInDraftOut | None:
    return await actions.latest(db, current.id)


@router.post("", status_code=202)
async def launch(body: LinkedInStart, user: InterfaceUserDep, rt: Runtime) -> LinkedInDraftOut:
    return await actions.start(rt, user.id, body)


@router.put("/{draft_id}")
async def save(
    draft_id: DraftId, body: LinkedInEdit, user: InterfaceUserDep, db: Db
) -> LinkedInDraftOut:
    return await actions.edit(db, user.id, draft_id, body)
