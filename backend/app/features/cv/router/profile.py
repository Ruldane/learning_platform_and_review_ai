"""API du profil maître (SPEC 5.1, 14.2 ; D124). `POST /profile/import` range le CV (et le profil
LinkedIn) dans la mémoire puis lance la capture de l'Archiviste ; `GET /profile` rend la version
validée et le brouillon plus récent ; `PUT /profile` crée une version validée ;
`GET /profile/versions` liste les versions. Une 422 nomme les champs, jamais leur valeur."""

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
    """Le CV ouvert par le lifespan (`app.state.career.cv`)."""
    runtime: CvRuntime = conn.app.state.career.cv
    return runtime


CvDep = Annotated[CvRuntime, Depends(get_cv_runtime)]


@router.get("/profile", response_model=ProfileStateOut)
async def get_profile(current: CurrentUserDep, db: Db) -> ProfileStateOut:
    """La version validée, le brouillon s'il est plus récent, la capture en cours."""
    return await profile_state(db, current.id)


@router.put("/profile", response_model=ProfileOut)
async def put_profile(body: ProfilePutIn, current: CurrentUserDep, rt: CvDep) -> ProfileOut:
    """Nouvelle version validée (source `january`), ids des faits gardés, compétences du profil
    déclarées. 409 `profile_conflict` : `base_version` n'est pas la dernière version."""
    return await save_profile(rt, current.id, body)


@router.post(
    "/profile/import", response_model=ProfileImportStarted, status_code=status.HTTP_202_ACCEPTED
)
async def import_profile(
    current: CurrentUserDep,
    db: Db,
    rt: CvDep,
    cv: Annotated[UploadFile, File()],
    linkedin: Annotated[UploadFile | None, File()] = None,
    note: Annotated[str | None, Form(max_length=MAX_NOTE_CHARS)] = None,
) -> ProfileImportStarted:
    """CV en PDF (10 Mo au plus), profil LinkedIn en PDF facultatif, note facultative. 409
    `capture_in_progress`, 413 `file_too_large`, 415 `unsupported_file_type`."""
    return await start_import(rt, db, current.id, cv=cv, linkedin=linkedin, note=note)


@router.get("/profile/versions", response_model=list[ProfileVersionOut])
async def get_profile_versions(current: CurrentUserDep, db: Db) -> list[ProfileVersionOut]:
    """Toutes les versions, la plus récente d'abord."""
    return await profile_versions(db, current.id)
