"""API of the targeted CV versions (SPEC 5.3, 14.2; D130): list, detail, PDF and page images.
The PDF is downloaded under its ASCII name (`CV_<Name>_<Company>_<Role>.pdf`)."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Response

from app.core.deps import CurrentUserDep
from app.features.cv.router.fields import FieldPathsRoute
from app.features.cv.router.profile import CvDep
from app.features.cv.router.reviews import errors
from app.features.cv.schemas_reviews import VersionOut
from app.features.cv.service.versions import (
    get_version,
    list_versions,
    version_page,
    version_pdf,
)

router = APIRouter(prefix="/cv/versions", tags=["cv-versions"], route_class=FieldPathsRoute)

Id = Annotated[str, Path(min_length=1, max_length=36)]
_PDF: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/pdf": {}}, "description": "The targeted CV as PDF."},
    **errors(e404="`version_not_found`, `version_not_ready` (not `ready` yet)"),
}
_PNG: dict[int | str, dict[str, Any]] = {
    200: {"content": {"image/png": {}}, "description": "PNG image of the page."},
    **errors(e404="`version_not_found`, `version_page_not_found`"),
}


@router.get("", response_model=list[VersionOut])
async def get_versions(
    current: CurrentUserDep,
    rt: CvDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[VersionOut]:
    """The versions (of a posting), newest first."""
    return await list_versions(rt, current.id, posting_id)


@router.get(
    "/{version_id}", response_model=VersionOut, responses=errors(e404="`version_not_found`")
)
async def get_one_version(version_id: Id, current: CurrentUserDep, rt: CvDep) -> VersionOut:
    return await get_version(rt, current.id, version_id)


@router.get("/{version_id}/pdf", response_class=Response, responses=_PDF)
async def get_version_pdf(version_id: Id, current: CurrentUserDep, rt: CvDep) -> Response:
    """Download (`attachment`); 404 as long as the version is not `ready`."""
    filename, body = await version_pdf(rt, current.id, version_id)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    return Response(content=body, media_type="application/pdf", headers=headers)


@router.get("/{version_id}/pages/{number}", response_class=Response, responses=_PNG)
async def get_version_page(
    version_id: Id, number: int, current: CurrentUserDep, rt: CvDep
) -> Response:
    """Page `number` (from 1) of a ready version; 404 otherwise."""
    data = await version_page(rt, current.id, version_id, number)
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})
