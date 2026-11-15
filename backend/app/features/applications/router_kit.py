"""API du kit de candidature (SPEC 6.4, F16, D143) : lancement du parcours `application_kit`, les
sept pièces d'une fiche, la modification d'une pièce par January et l'archive. Toutes au nom de
l'utilisatrice courante ; une 422 nomme les champs, sans jamais citer le texte."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Response
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.applications.router import ApplicationsDep, Id
from app.features.applications.schemas_kit import KitItemOut, KitKind, KitOut, KitPatch, KitStartOut
from app.features.applications.service.kit import patch_piece, read_kit, start_kit
from app.features.applications.service.kit_zip import kit_archive
from app.features.cv.service.runtime import CvRuntime

router = APIRouter(prefix="/applications", tags=["applications"], route_class=FieldPathsRoute)

_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "`application_not_found`"}}
_ZIP: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/zip": {}}, "description": "Le kit en archive ZIP."},
    **_NOT_FOUND,
}


def get_cv_runtime(conn: HTTPConnection) -> CvRuntime:
    """Le CV de la carrière (`app.state.career.cv`) : l'archive y relit le PDF de la version."""
    runtime: CvRuntime = conn.app.state.career.cv
    return runtime


CvDep = Annotated[CvRuntime, Depends(get_cv_runtime)]
Kind = Annotated[KitKind, Path()]


@router.post(
    "/{application_id}/kit",
    response_model=KitStartOut,
    status_code=202,
    responses={
        404: {"description": "`application_not_found`"},
        409: {
            "description": (
                "`kit_in_progress` (`details.session_id` : la session ouverte), "
                "`posting_required` (la fiche n'a ni offre ni texte d'offre), "
                "`profile_required` (aucun profil maître validé)"
            )
        },
    },
)
async def post_kit(application_id: Id, current: CurrentUserDep, rt: ApplicationsDep) -> KitStartOut:
    """Lance les sept pièces en parallèle ; elles arrivent par `artifact.ready` (`kind`
    `kit_item`). Relancer refait les pièces que January n'a pas modifiées."""
    return KitStartOut(session_id=await start_kit(rt, current.id, application_id))


@router.get("/{application_id}/kit", response_model=KitOut, responses=_NOT_FOUND)
async def get_kit(application_id: Id, current: CurrentUserDep, rt: ApplicationsDep) -> KitOut:
    """Les sept pièces dans l'ordre fixe (`pending` : pas encore rangée)."""
    return await read_kit(rt, current.id, application_id)


@router.patch(
    "/{application_id}/kit/{kind}",
    response_model=KitItemOut,
    responses={
        404: {"description": "`application_not_found`, `kit_item_not_found`"},
        409: {
            "description": (
                "`profile_required`, `posting_required` : la modification d'une pièce à "
                "vérifier ne peut pas être relue sans le profil validé ni le texte de l'offre"
            )
        },
    },
)
async def patch_kit_item(
    application_id: Id, kind: Kind, body: KitPatch, current: CurrentUserDep, rt: ApplicationsDep
) -> KitItemOut:
    """Le texte de January remplace la pièce (gardée aux relances). Une pièce « à vérifier » est
    relue : `flags` mis à jour, « prête » si rien ne reste."""
    return await patch_piece(rt, current.id, application_id, kind, body.content)


@router.get("/{application_id}/kit.zip", response_class=Response, responses=_ZIP)
async def get_kit_zip(
    application_id: Id, current: CurrentUserDep, rt: ApplicationsDep, cv: CvDep
) -> Response:
    """Téléchargement (`attachment`) : une pièce par fichier Markdown, le PDF du CV et
    `LISEZMOI.txt`."""
    filename, body = await kit_archive(rt, cv, current.id, application_id)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    return Response(content=body, media_type="application/zip", headers=headers)
