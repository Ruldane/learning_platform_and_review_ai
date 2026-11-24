"""Création d'un gabarit de CV et lancement de la capture du design (SPEC 5.2, 14.2 ; D126).

Le PDF d'origine est toujours rangé comme document de la mémoire (`document_id` jamais vide,
preflight G26) ; sa mise en page est extraite **avant** tout lancement (PDF illisible ou de plus de
4 pages : 422, rien n'est rangé) et gardée dans le gabarit (images, géométrie, blocs, texte,
rôles des polices) : le Maquettiste ne l'extrait plus. Une capture de gabarit à la fois (409
`capture_in_progress`) ; sans modèle de vision, 409 `vision_unavailable` (11.2). Journaux :
identifiants et nombres, jamais le nom du gabarit, un fichier ni une police."""

import logging

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.played import played_by
from app.db.models.career import CvTemplate
from app.features.cv.repository import TemplateRepository
from app.features.cv.schemas_templates import TemplateCreated
from app.features.cv.service.fonts import font_gaps, font_roles, font_uses, roles_to_json
from app.features.cv.service.profile_import import check_pdf, pdf_only
from app.features.cv.service.profile_store import document_not_found
from app.features.cv.service.runtime import CAPTURE_GRAPH, TEMPLATE_SUBJECT, CvRuntime
from app.features.cv.service.templates import capture_in_progress, settle
from app.features.cv.service.templates_data import blocks_summary, geometry, visible_text
from app.features.cv.service.templates_store import IMAGE_CATEGORY
from app.features.memory.service.document_files import document_file
from app.features.memory.service.documents import DocumentService
from app.features.settings.service import SettingsService
from app.providers.llm.model_defaults import supports_vision
from app.providers.pdf.base import PdfLayout

logger = logging.getLogger(__name__)

DESIGNER = "designer"  # l'agent qui capture le design (niveau `vision`, D125)
LAUNCH_FAILED = "Template capture could not start. Try again."


def vision_unavailable() -> AppError:
    return AppError(
        "vision_unavailable",
        "Template capture needs a model that can read images. Enable one in Settings.",
        409,
    )


def one_source() -> AppError:
    return AppError(
        "validation_error",
        "Invalid request. Check the highlighted fields.",
        422,
        {"fields": ["file", "document_id"]},
    )


async def vision_enabled(db: AsyncSession, user_id: str) -> bool:
    """Le modèle du Maquettiste (son réglage propre, sinon le niveau `vision`) lit les images."""
    settings = await SettingsService(db, user_id).get()
    return supports_vision(settings.agent_overrides.get(DESIGNER, settings.tiers["vision"]))


async def _source(
    rt: CvRuntime, user_id: str, file: UploadFile | None, document_id: str | None
) -> bytes:
    if file is not None:
        await check_pdf(file)
        data = await file.read()
        await file.seek(0)
        return data
    stored = await document_file(rt.memory, user_id, str(document_id))
    if stored is None:
        raise document_not_found()
    if stored.source_kind != "pdf":
        raise pdf_only()
    return stored.data


async def _row(
    rt: CvRuntime, db: AsyncSession, user_id: str, name: str, document_id: str, layout: PdfLayout
) -> CvTemplate:
    roles = font_roles(layout)
    families = {role.family for role in roles}  # supposées chargées ; `prepare` corrige
    first = layout.pages[0]
    images = [page.image_png for page in layout.pages]
    keys = [await rt.storage.save(user_id, IMAGE_CATEGORY, png, ".png") for png in images]
    return await TemplateRepository(db, user_id).add(
        document_id=document_id,
        name=name,
        status="capturing",
        page_count=len(layout.pages),
        page_size={"width_pt": first.width_pt, "height_pt": first.height_pt},
        original_pages=keys,
        selectable=layout.selectable,
        fonts=[use.model_dump() for use in font_uses(roles, families)],
        font_gaps=font_gaps(roles, families),
        prepared={
            "pages": geometry(layout),
            "blocks_summary": blocks_summary(layout),
            "original_text": visible_text(layout),
            "roles": roles_to_json(roles),
        },
    )


async def _launch(rt: CvRuntime, db: AsyncSession, user_id: str, row: CvTemplate) -> str:
    body = {"mode": "design", "template_id": row.id}
    try:
        session_id = await rt.launcher.start(
            user_id, CAPTURE_GRAPH, body, subject_type=TEMPLATE_SUBJECT, subject_id=row.id
        )
    except Exception:
        row.status, row.failure_reason = "failed", LAUNCH_FAILED
        await db.commit()
        raise
    row.session_id = session_id
    await db.commit()
    return session_id


async def create_template(
    rt: CvRuntime,
    user_id: str,
    *,
    name: str,
    file: UploadFile | None,
    document_id: str | None,
) -> TemplateCreated:
    if (file is None) == (document_id is None):
        raise one_source()
    if not played_by(user_id):
        async with rt.session_factory() as db:
            if not await vision_enabled(db, user_id):
                raise vision_unavailable()
    layout = await rt.layout.extract_layout(await _source(rt, user_id, file, document_id))
    async with rt.template_lock(user_id), rt.session_factory() as db:
        open_ids = await settle(db, user_id)
        if running := [sid for ids in open_ids.values() for sid in ids]:
            raise capture_in_progress(running[0])
        if file is not None:
            service = DocumentService(db, user_id, rt.memory)
            document, _ = await service.create(
                file=file, url=None, text=None, title=None, tags=["cv"]
            )
            document_id = document.id
        row = await _row(rt, db, user_id, name, str(document_id), layout)
        await db.commit()  # le Maquettiste relit le gabarit dans sa propre session
        session_id = await _launch(rt, db, user_id, row)
        template_id = row.id
    logger.info(
        "Capture du design lancée : utilisateur %s, gabarit %s, session %s, %d page(s)",
        user_id,
        template_id,
        session_id,
        len(layout.pages),
    )
    return TemplateCreated(template_id=template_id, session_id=session_id)
