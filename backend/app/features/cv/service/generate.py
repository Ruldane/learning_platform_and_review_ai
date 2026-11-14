"""Rendu d'une version du CV ciblé (SPEC 5.3 étapes 8 et 9 ; D130), appelé par le port de la
revue (`AgentCvReviewStore.render_version`) depuis la sortie du parcours `cv_review`.

Le contenu a été composé et figé au clic sur « Générer » (`cv_versions.content`, décisions
comprises) ; ici, il est seulement rendu avec le gabarit figé. Si le PDF a plus de pages que
l'original et que January n'a pas autorisé de page de plus, les trois paliers de resserrement
(`TIGHTEN_STEPS`) s'appliquent un à un, chacun re-rendu ; encore trop long : `pages_exceeded`
(January choisit : retirer une ligne ou autoriser une page de plus). Le PDF prêt et les images de
ses pages sont rangés (`cv_versions`), avec les indicateurs après : couverture des lignes adossées
à un fait et contrôles ATS du PDF rendu.

Idempotent : une version déjà rendue (`ready`, `pages_exceeded`, `failed`) est relue, jamais
rendue deux fois. Journaux : version, pages, durée ; jamais le nom du fichier (17.2)."""

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
from app.features.cv.service.template import cv_document
from app.features.cv.service.tighten import LOOSE_MIN_BODY_PT, TIGHTEN_STEPS
from app.features.postings.service.queries import get_posting
from app.providers.fonts.base import FontFile
from app.providers.pdf.base import PdfLayout, PdfUnreadable, RenderFailed

logger = logging.getLogger(__name__)

RENDER_FAILED = "Le PDF n'a pas pu être généré : réessaie dans un instant."
NO_TEMPLATE = "Le modèle de CV de cette revue n'est plus lisible : relance une revue."


@dataclass(frozen=True)
class Rendered:
    pdf: bytes
    layout: PdfLayout
    tightened: int  # paliers de resserrement appliqués


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
    """Les polices rangées du gabarit (résolues pendant la capture) ; aucune sinon."""
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
    """Rendu, puis paliers de resserrement tant que le PDF dépasse `original` pages (sauf
    `allow_extra`) ; rend le dernier rendu."""
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
    """PDF, images des pages et indicateurs après, sur la ligne relue (encore `rendering`)."""
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
    """Plancher du corps (preflight G20) : `MIN_BODY_PT` si l'original passait `font_sizes`."""
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
        CvContent.model_validate(row.content),
        original=row.original_page_count,
        allow_extra=row.allow_extra_pages,
        min_body_pt=await _min_body(db, user_id, row.review_id),
    )


async def render_version(
    rt: CvRuntime, db: AsyncSession, user_id: str, version_id: str
) -> VersionOutcome:
    """Voir l'en-tête du module ; 404 `version_not_found` pour la version d'une autre."""
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
    if fresh.status != "rendering":  # rendue entre-temps : la première écrite gagne
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
        "Version du CV : version %s, statut %s, %s page(s) pour %d, %s palier(s), %.1f s%s",
        version_id,
        fresh.status,
        fresh.page_count,
        fresh.original_page_count,
        done.tightened if done else 0,
        time.monotonic() - started,
        f" ({failure})" if failure else "",
    )
    return outcome(fresh)
