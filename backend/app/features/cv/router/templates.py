"""API des gabarits de CV (SPEC 5.2, 14.2 ; D126). `POST /cv/templates` range le CV d'origine
(PDF envoyé ou CV déjà importé) et lance la capture du design par le Maquettiste ; les autres
routes lisent les gabarits, leurs images, choisissent le gabarit actif et archivent. Une 422 nomme
les champs, jamais leur valeur."""

from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Response, UploadFile, status

from app.core.deps import CurrentUserDep
from app.features.cv.router.fields import FieldPathsRoute
from app.features.cv.router.profile import CvDep
from app.features.cv.schemas_templates import (
    TemplateCreated,
    TemplateOut,
    TemplateSummaryOut,
)
from app.features.cv.service.templates import (
    activate_template,
    archive_template,
    get_template,
    list_templates,
    page_png,
)
from app.features.cv.service.templates_create import create_template

router = APIRouter(prefix="/cv/templates", tags=["cv-templates"], route_class=FieldPathsRoute)

TemplateId = Annotated[str, Path(min_length=1, max_length=36)]


@router.post("", response_model=TemplateCreated, status_code=status.HTTP_202_ACCEPTED)
async def post_template(
    current: CurrentUserDep,
    rt: CvDep,
    name: Annotated[str, Form(min_length=1, max_length=120, pattern=r"\S")],
    file: Annotated[UploadFile | None, File()] = None,
    document_id: Annotated[str | None, Form(min_length=1, max_length=36)] = None,
) -> TemplateCreated:
    """CV en PDF (10 Mo au plus, 4 pages au plus) OU `document_id` d'un CV importé. 409
    `vision_unavailable`, 409 `capture_in_progress`, 413 `file_too_large`, 415
    `unsupported_file_type`, 422 `pdf_unreadable`."""
    return await create_template(
        rt, current.id, name=name.strip(), file=file, document_id=document_id
    )


@router.get("", response_model=list[TemplateSummaryOut])
async def get_templates(current: CurrentUserDep, rt: CvDep) -> list[TemplateSummaryOut]:
    """Les gabarits non archivés, le plus récent d'abord."""
    return await list_templates(rt, current.id)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_one_template(
    template_id: TemplateId, current: CurrentUserDep, rt: CvDep
) -> TemplateOut:
    return await get_template(rt, current.id, template_id)


@router.get(
    "/{template_id}/pages/{kind}/{number}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "Image PNG de la page."}},
)
async def get_template_page(
    template_id: TemplateId,
    kind: str,
    number: int,
    current: CurrentUserDep,
    rt: CvDep,
) -> Response:
    """Page `number` (depuis 1) du CV d'origine ou du rendu de la passe courante ; 404 sinon."""
    data = await page_png(rt, current.id, template_id, kind, number)
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/{template_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def post_activate(template_id: TemplateId, current: CurrentUserDep, rt: CvDep) -> None:
    """Le gabarit devient le seul actif ; 409 `template_not_ready` s'il n'est pas prêt."""
    await activate_template(rt, current.id, template_id)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: TemplateId, current: CurrentUserDep, rt: CvDep) -> None:
    """Archivé (statut `archived`) ; 409 `template_in_use` si une revue en cours l'emploie."""
    await archive_template(rt, current.id, template_id)
