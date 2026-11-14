"""API des versions du CV ciblé (SPEC 5.3, 14.2 ; D130) : liste, détail, PDF et images des
pages. Le PDF est téléchargé sous son nom ASCII (`CV_<Nom>_<Entreprise>_<Poste>.pdf`)."""

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
    200: {"content": {"application/pdf": {}}, "description": "Le CV ciblé en PDF."},
    **errors(e404="`version_not_found`, `version_not_ready` (pas encore `ready`)"),
}
_PNG: dict[int | str, dict[str, Any]] = {
    200: {"content": {"image/png": {}}, "description": "Image PNG de la page."},
    **errors(e404="`version_not_found`, `version_page_not_found`"),
}


@router.get("", response_model=list[VersionOut])
async def get_versions(
    current: CurrentUserDep,
    rt: CvDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[VersionOut]:
    """Les versions (d'une offre), la plus récente d'abord."""
    return await list_versions(rt, current.id, posting_id)


@router.get(
    "/{version_id}", response_model=VersionOut, responses=errors(e404="`version_not_found`")
)
async def get_one_version(version_id: Id, current: CurrentUserDep, rt: CvDep) -> VersionOut:
    return await get_version(rt, current.id, version_id)


@router.get("/{version_id}/pdf", response_class=Response, responses=_PDF)
async def get_version_pdf(version_id: Id, current: CurrentUserDep, rt: CvDep) -> Response:
    """Téléchargement (`attachment`) ; 404 tant que la version n'est pas `ready`."""
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
    """Page `number` (depuis 1) d'une version prête ; 404 sinon."""
    data = await version_page(rt, current.id, version_id, number)
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})
