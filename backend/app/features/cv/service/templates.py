"""CV templates on the API side (SPEC 5.2, 14.2; D126): list, detail, page images, active
template, archiving; creation is in `templates_create`.

The status follows the outcome of the session: a `capturing` template whose session is no
longer open (model failure, cap, timeout, cancellation, stop) becomes `failed` on the next read,
under the templates lock (a finished session never resumes: the fix is safe). Logs: ids and
numbers, never the template name, a file or a font."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.career import CvTemplate
from app.features.cv.repository import TemplateRepository
from app.features.cv.schemas_templates import (
    FontUseOut,
    TemplateOut,
    TemplateSummaryOut,
    ZoneDiffOut,
)
from app.features.cv.service.runtime import CAPTURE_GRAPH, TEMPLATE_SUBJECT, CvRuntime
from app.features.cv.service.templates_data import (
    template_not_found,
)
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

INTERRUPTED = "Template capture stopped early. Restart it to continue."


def capture_in_progress(session_id: str) -> AppError:
    return AppError(
        "capture_in_progress",
        "A CV template is already being recreated.",
        409,
        {"session_id": session_id},
    )


def template_not_ready() -> AppError:
    return AppError(
        "template_not_ready", "Finish recreating this CV template before using it.", 409
    )


def template_in_use() -> AppError:
    return AppError(
        "template_in_use", "Finish the review using this template before deleting it.", 409
    )


def page_not_found() -> AppError:
    return AppError("template_page_not_found", "Template page not found.", 404)


async def _open_captures(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    return await list_open_sessions_by_subject(
        db, user_id, graph=CAPTURE_GRAPH, subject_type=TEMPLATE_SUBJECT
    )


async def settle(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    """Templates being captured without an open session → `failed`; returns the open sessions.
    Sessions read BEFORE the templates (D97 no. 9). The caller holds `template_lock`."""
    open_ids = await _open_captures(db, user_id)
    stale = [
        row
        for row in await TemplateRepository(db, user_id).capturing()
        if row.session_id is None or row.session_id not in open_ids.get(row.id, [])
    ]
    for row in stale:
        row.status, row.failure_reason = "failed", INTERRUPTED
        logger.info("Template without session: user %s, template %s", user_id, row.id)
    if stale:
        await db.commit()
    return open_ids


def to_summary(row: CvTemplate) -> TemplateSummaryOut:
    return TemplateSummaryOut.model_validate(_summary_fields(row))


def _summary_fields(row: CvTemplate) -> dict[str, object]:
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "active": row.active,
        "score": row.score,
        "passes": row.passes,
        "page_count": row.page_count,
        "created_at": row.created_at,
    }


def to_out(row: CvTemplate) -> TemplateOut:
    zones = (row.score_detail or {}).get("zones", [])
    return TemplateOut.model_validate(
        {
            **_summary_fields(row),
            "selectable": row.selectable,
            "fonts": [FontUseOut.model_validate(use) for use in row.fonts],
            "font_gaps": [str(gap) for gap in row.font_gaps],
            "zones": [ZoneDiffOut.model_validate(zone) for zone in zones],
            "session_id": row.session_id,
            "failure_reason": row.failure_reason,
        }
    )


async def _visible(db: AsyncSession, user_id: str, template_id: str) -> CvTemplate:
    row = await TemplateRepository(db, user_id).get(template_id)
    if row is None or row.status == "archived":
        raise template_not_found()
    return row


async def list_templates(rt: CvRuntime, user_id: str) -> list[TemplateSummaryOut]:
    async with rt.template_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return [to_summary(row) for row in await TemplateRepository(db, user_id).visible()]


async def get_template(rt: CvRuntime, user_id: str, template_id: str) -> TemplateOut:
    async with rt.template_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return to_out(await _visible(db, user_id, template_id))


async def page_png(rt: CvRuntime, user_id: str, template_id: str, kind: str, number: int) -> bytes:
    """Image of a page (`number` from 1) of the original or of the current pass's rendering;
    404 for another kind (`PageKind`) or another number."""
    if kind not in ("original", "render"):
        raise page_not_found()
    async with rt.session_factory() as db:
        row = await _visible(db, user_id, template_id)
    keys = row.original_pages if kind == "original" else row.render_pages
    if not 1 <= number <= len(keys):
        raise page_not_found()
    return await rt.storage.read(user_id, str(keys[number - 1]))


async def activate_template(rt: CvRuntime, user_id: str, template_id: str) -> None:
    async with rt.template_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = await _visible(db, user_id, template_id)
        if row.status != "ready":
            raise template_not_ready()
        current = await TemplateRepository(db, user_id).active()
        if current is not None and current.id != row.id:
            current.active = False
            await db.flush()  # a single active one: the partial unique index is checked row by row
        row.active = True
        await db.commit()
    logger.info("Gabarit actif : utilisateur %s, gabarit %s", user_id, template_id)


async def archive_template(rt: CvRuntime, user_id: str, template_id: str) -> None:
    """Status `archived` (images, fonts and document kept); idempotent."""
    async with rt.template_lock(user_id), rt.session_factory() as db:
        open_ids = await settle(db, user_id)
        row = await TemplateRepository(db, user_id).get(template_id)
        if row is None:
            raise template_not_found()
        if row.status == "archived":
            return
        if row.status == "capturing" and open_ids.get(row.id):
            raise capture_in_progress(open_ids[row.id][0])
        if await TemplateRepository(db, user_id).in_review(template_id):
            raise template_in_use()
        row.status, row.active = "archived", False
        await db.commit()
    logger.info("Template archived: user %s, template %s", user_id, template_id)
