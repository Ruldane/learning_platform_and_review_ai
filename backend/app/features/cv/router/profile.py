"""Master profile API (SPEC 5.1, 14.2; D124). `POST /profile/import` files the CV (and the
LinkedIn profile) in memory then starts the Archivist's capture; `GET /profile` returns the
validated version and the newer draft; `PUT /profile` creates a validated version;
`GET /profile/versions` lists the versions. A 422 names the fields, never their value."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from starlette.requests import HTTPConnection

from app.agents.tools.profile_port import MAX_NOTE_CHARS
from app.core.deps import CurrentUserDep, Db
from app.features.cv.router.fields import FieldPathsRoute
from app.features.cv.schemas_profile import (
    ProfileImportStarted,
    ProfileOut,
    ProfilePutIn,
    ProfileStateOut,
    ProfileVersionOut,
)
from app.features.cv.service.profile import profile_state, profile_versions, save_profile
from app.features.cv.service.profile_import import start_import
from app.features.cv.service.runtime import CvRuntime

router = APIRouter(tags=["profile"], route_class=FieldPathsRoute)


def get_cv_runtime(conn: HTTPConnection) -> CvRuntime:
    """The CV opened by the lifespan (`app.state.career.cv`)."""
    runtime: CvRuntime = conn.app.state.career.cv
    return runtime


CvDep = Annotated[CvRuntime, Depends(get_cv_runtime)]


@router.get("/profile", response_model=ProfileStateOut)
async def get_profile(current: CurrentUserDep, db: Db) -> ProfileStateOut:
    """The validated version, the draft if it is newer, the capture in progress."""
    return await profile_state(db, current.id)


@router.put("/profile", response_model=ProfileOut)
async def put_profile(body: ProfilePutIn, current: CurrentUserDep, rt: CvDep) -> ProfileOut:
    """New validated version (source `january`), ids of the kept facts, declared profile
    skills. 409 `profile_conflict`: `base_version` is not the latest version."""
    return await save_profile(rt, current.id, body)


@router.post(
    "/profile/import", response_model=ProfileImportStarted, status_code=status.HTTP_202_ACCEPTED
)
async def import_profile(
    current: CurrentUserDep,
    db: Db,
    rt: CvDep,
    cv: Annotated[UploadFile | None, File()] = None,
    linkedin: Annotated[UploadFile | None, File()] = None,
    note: Annotated[str | None, Form(max_length=MAX_NOTE_CHARS)] = None,
    cv_document_id: Annotated[str | None, Form(min_length=36, max_length=36)] = None,
    linkedin_document_id: Annotated[str | None, Form(min_length=36, max_length=36)] = None,
) -> ProfileImportStarted:
    """CV as PDF (10 MB at most), optional LinkedIn profile as PDF, optional note. 409
    `capture_in_progress`, 413 `file_too_large`, 415 `unsupported_file_type`."""
    return await start_import(
        rt,
        db,
        current.id,
        cv=cv,
        linkedin=linkedin,
        note=note,
        cv_document_id=cv_document_id,
        linkedin_document_id=linkedin_document_id,
    )


@router.get("/profile/versions", response_model=list[ProfileVersionOut])
async def get_profile_versions(current: CurrentUserDep, db: Db) -> list[ProfileVersionOut]:
    """All versions, newest first."""
    return await profile_versions(db, current.id)
