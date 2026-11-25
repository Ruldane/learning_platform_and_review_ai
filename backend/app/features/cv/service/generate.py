"""Rendering a targeted CV version (SPEC 5.3 steps 8 and 9; D130), called by the review port
(`AgentCvReviewStore.render_version`) from the exit of the `cv_review` flow.

The content was composed and frozen at the "Generate" click (`cv_versions.content`, decisions
included); here, it is only rendered with the frozen template. If the PDF has more pages than
the original and January has not allowed one more page, the three tightening tiers
(`TIGHTEN_STEPS`) apply one by one, each re-rendered; still too long: `pages_exceeded`
(January chooses: remove a line or allow one more page). The ready PDF and its page images are
stored (`cv_versions`), with the after indicators: coverage of the lines backed by a fact and
ATS checks of the rendered PDF.

Idempotent: an already rendered version (`ready`, `pages_exceeded`, `failed`) is re-read, never
rendered twice. Logs: version, pages, duration; never the file name (17.2)."""

import logging
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_indicators import coverage
from app.agents.tools.cv_review_port import VersionOutcome
from app.agents.tools.cv_schema import CvContent
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.template_schema import TemplateSpec
from app.db.models.career import CvTemplate, CvVersion
from app.features.cv.repository import ReviewRepository, TemplateRepository, VersionRepository
from app.features.cv.service.ats_checks import MIN_BODY_PT, ats_checks
from app.features.cv.service.fonts import StoredFont, load_files
from app.features.cv.service.review_data import (
    VERSION_CATEGORY,
    checks_json,
    content_lines,
    coverage_json,
    version_not_found,
)
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.targeted_content import TargetedCvContent
from app.features.cv.service.template import cv_document
from app.features.cv.service.tighten import LOOSE_MIN_BODY_PT, TIGHTEN_STEPS
from app.features.postings.service.queries import get_posting
from app.providers.fonts.base import FontFile
from app.providers.pdf.base import PdfLayout, PdfUnreadable, RenderFailed

logger = logging.getLogger(__name__)

RENDER_FAILED = "The PDF could not be generated. Try again in a moment."
NO_TEMPLATE = "The CV template could not be read. Start a new review."


@dataclass(frozen=True)
class Rendered:
    pdf: bytes
    layout: PdfLayout
    tightened: int  # tightening tiers applied


def outcome(row: CvVersion) -> VersionOutcome:
    return VersionOutcome(
        version_id=row.id,
        status=row.status,  # type: ignore[arg-type]  # colonne texte, valeurs de VersionStatus
        page_count=row.page_count,
        filename=row.filename,
        original_page_count=row.original_page_count,
    )


async def _fonts(
    rt: CvRuntime, user_id: str, template: CvTemplate, spec: TemplateSpec
) -> list[FontFile]:
    """The template's stored fonts (resolved during the capture); none otherwise."""
    stored = [StoredFont.from_json(f) for f in (template.prepared or {}).get("font_files", [])]
    return await load_files(rt, user_id, stored, {spec.fonts.body, spec.fonts.heading})


async def _once(
    rt: CvRuntime, spec: TemplateSpec, content: CvContent, fonts: list[FontFile]
) -> tuple[bytes, PdfLayout]:
    pdf = await rt.html_pdf.html_to_pdf(cv_document(spec, content, fonts))
    return pdf, await rt.layout.extract_layout(pdf)


async def render_fitting(
    rt: CvRuntime,
    user_id: str,
    template: CvTemplate,
    content: CvContent,
    *,
    original: int,
    allow_extra: bool,
    min_body_pt: float,
) -> Rendered:
    """Render, then tightening tiers as long as the PDF exceeds `original` pages (unless
    `allow_extra`); returns the last render."""
    spec = TemplateSpec.model_validate(template.spec)
    fonts = await _fonts(rt, user_id, template, spec)
    pdf, layout = await _once(rt, spec, content, fonts)
    tightened = 0
    for step in TIGHTEN_STEPS:
        if allow_extra or len(layout.pages) <= original:
            break
        spec = step(spec, min_body_pt)
        pdf, layout = await _once(rt, spec, content, fonts)
        tightened += 1
    return Rendered(pdf, layout, tightened)


async def _store(
    rt: CvRuntime, user_id: str, row: CvVersion, done: Rendered, analysis: PostingAnalysis | None
) -> None:
    """PDF, page images and after indicators, on the re-read row (still `rendering`)."""
    content = CvContent.model_validate(row.content)
    keys = [
        await rt.storage.save(user_id, VERSION_CATEGORY, page.image_png, ".png")
        for page in done.layout.pages
    ]
    row.storage_key = await rt.storage.save(user_id, VERSION_CATEGORY, done.pdf, ".pdf")
    row.page_images = keys
    requirements = analysis.requirements if analysis else []
    keywords = analysis.keywords if analysis else []
    row.coverage = coverage_json(coverage(requirements, keywords, content_lines(content)))
    row.ats = checks_json(ats_checks(done.layout, content))
    row.status = "ready"


async def _min_body(db: AsyncSession, user_id: str, review_id: str) -> float:
    """Body floor (preflight G20): `MIN_BODY_PT` if the original passed `font_sizes`."""
    review = await ReviewRepository(db, user_id).get(review_id)
    checks = ((review.before if review else None) or {}).get("checks", [])
    passed = any(c.get("id") == "font_sizes" and c.get("passed") for c in checks)
    return MIN_BODY_PT if passed else LOOSE_MIN_BODY_PT


async def _render(rt: CvRuntime, db: AsyncSession, user_id: str, row: CvVersion) -> Rendered:
    template = await TemplateRepository(db, user_id).get(row.template_id)
    if template is None or template.spec is None:
        raise RenderFailed()
    return await render_fitting(
        rt,
        user_id,
        template,
        TargetedCvContent.model_validate(row.content),
        original=row.original_page_count,
        allow_extra=row.allow_extra_pages,
        min_body_pt=await _min_body(db, user_id, row.review_id),
    )


async def render_version(
    rt: CvRuntime, db: AsyncSession, user_id: str, version_id: str
) -> VersionOutcome:
    """See the module header; 404 `version_not_found` for another user's version."""
    repo = VersionRepository(db, user_id)
    row = await repo.get_fresh(version_id)
    if row is None:
        raise version_not_found()
    if row.status != "rendering":
        return outcome(row)
    posting = await get_posting(db, user_id, row.posting_id)
    analysis = PostingAnalysis.model_validate(posting.analysis) if posting.analysis else None
    started, failure = time.monotonic(), ""
    try:
        done: Rendered | None = await _render(rt, db, user_id, row)
    except (RenderFailed, PdfUnreadable) as exc:
        done, failure = None, type(exc).__name__
    fresh = await repo.get_fresh(version_id)
    if fresh is None:
        raise version_not_found()
    if fresh.status != "rendering":  # rendered meanwhile: the first one written wins
        return outcome(fresh)
    if done is None:
        fresh.status, fresh.failure_reason = "failed", RENDER_FAILED
    else:
        fresh.page_count = len(done.layout.pages)
        if fresh.page_count > fresh.original_page_count and not fresh.allow_extra_pages:
            fresh.status = "pages_exceeded"
        else:
            await _store(rt, user_id, fresh, done, analysis)
    await db.commit()
    logger.info(
        "CV version: version %s, status %s, %s page(s) for %d, %s tier(s), %.1f s%s",
        version_id,
        fresh.status,
        fresh.page_count,
        fresh.original_page_count,
        done.tightened if done else 0,
        time.monotonic() - started,
        f" ({failure})" if failure else "",
    )
    return outcome(fresh)
