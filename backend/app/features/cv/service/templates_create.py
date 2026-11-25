"""Creating a CV template and launching the design capture (SPEC 5.2, 14.2; D126).

The original PDF is always stored as a memory document (`document_id` never empty, preflight
G26); its layout is extracted **before** any launch (unreadable PDF or more than 4 pages: 422,
nothing is stored) and kept in the template (images, geometry, blocks, text, font roles): the
Designer no longer extracts it. One template capture at a time (409 `capture_in_progress`);
without a vision model, 409 `vision_unavailable` (11.2). Logs: ids and numbers, never the
template name, a file or a font."""

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

DESIGNER = "designer"  # the agent that captures the design (`vision` tier, D125)
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
    """The Designer's model (its own setting, otherwise the `vision` tier) reads the images."""
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
    families = {role.family for role in roles}  # assumed loaded; `prepare` corrects
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
        await db.commit()  # the Designer re-reads the template in its own session
        session_id = await _launch(rt, db, user_id, row)
        template_id = row.id
    logger.info(
        "Design capture started: user %s, template %s, session %s, %d page(s)",
        user_id,
        template_id,
        session_id,
        len(layout.pages),
    )
    return TemplateCreated(template_id=template_id, session_id=session_id)
