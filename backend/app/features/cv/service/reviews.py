"""Revues de CV côté API (SPEC 5.3, 14.2 ; D130) : lancement, liste et détail.

`POST /cv/reviews` vérifie et **fige** ce que la revue lira : le profil validé (sa version), le
gabarit actif, l'offre analysée ; il calcule les indicateurs avant (couverture des exigences par
le CV d'origine, contrôles ATS du PDF d'origine) puis lance le parcours `cv_review`. Une revue en
cours par offre (409 `review_in_progress`).

Le statut suit l'issue de la session (comme D126 n° 5) : une revue lancée ou proposée dont la
session n'est plus ouverte (panne du modèle, délai, annulation, offre qui n'en est pas une)
passe en `failed` à la lecture suivante, ses versions encore en rendu aussi, sous le verrou des
revues ; une session terminée ne reprend jamais : la correction est sûre. Journaux : identifiants
et nombres seulement."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_compose import base_content
from app.agents.tools.cv_indicators import AtsCheck, Indicators, coverage
from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.career import CvReview, CvTemplate
from app.features.cv.repository import (
    ModificationRepository,
    ProfileRepository,
    ReviewRepository,
    TemplateRepository,
    VersionRepository,
)
from app.features.cv.schemas_reviews import CvReviewOut, ReviewStarted
from app.features.cv.service.ats_checks import ats_checks
from app.features.cv.service.generate import RENDER_FAILED
from app.features.cv.service.review_data import (
    before_out,
    content_lines,
    indicators_json,
    modification_out,
    template_order,
    version_out,
)
from app.features.cv.service.review_store import review_row
from app.features.cv.service.runtime import REVIEW_GRAPH, REVIEW_SUBJECT, CvRuntime
from app.features.memory.service.document_files import document_file
from app.features.postings.service.queries import get_posting
from app.features.sessions.service import list_open_sessions_by_subject, session_facts

logger = logging.getLogger(__name__)

OUTPUT_KIND = "cv_output"  # la question de sortie du parcours (« Que veux-tu maintenant ? »)


def profile_required() -> AppError:
    return AppError(
        "profile_required", "Valide d'abord ton profil maître : la revue s'appuie sur lui.", 409
    )


def template_required() -> AppError:
    return AppError(
        "template_required", "Choisis d'abord un modèle de CV prêt : le CV ciblé le reprend.", 409
    )


def posting_not_ready() -> AppError:
    return AppError(
        "posting_not_ready", "Cette offre n'est pas encore analysée : attends son analyse.", 409
    )


def review_in_progress(review_id: str) -> AppError:
    return AppError(
        "review_in_progress",
        "Une revue de CV de cette offre est en cours : termine-la d'abord.",
        409,
        {"review_id": review_id},
    )


async def settle(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    """Revues en cours sans session ouverte → `failed` (versions en rendu aussi) ; rend les
    sessions ouvertes par revue. Sessions lues AVANT les revues (D97 n° 9). L'appelant tient
    `review_lock`."""
    open_ids = await list_open_sessions_by_subject(
        db, user_id, graph=REVIEW_GRAPH, subject_type=REVIEW_SUBJECT
    )
    stale = [
        row
        for row in await ReviewRepository(db, user_id).open_rows()
        if row.session_id is None or row.session_id not in open_ids.get(row.id, [])
    ]
    for row in stale:
        row.status = "failed"
        logger.info("Revue sans session : utilisateur %s, revue %s", user_id, row.id)
    for version in await VersionRepository(db, user_id).rendering([row.id for row in stale]):
        version.status, version.failure_reason = "failed", RENDER_FAILED
    if stale:
        await db.commit()
    return open_ids


async def waiting_output(db: AsyncSession, user_id: str, review: CvReview) -> str | None:
    """L'`interrupt_id` de la question de sortie si la session de la revue l'attend."""
    if review.session_id is None or review.status != "proposed":
        return None
    facts = await session_facts(db, user_id, review.session_id)
    pending = facts.pending if facts is not None else None
    if facts is None or facts.status != "waiting_user" or not pending:
        return None
    return str(pending["interrupt_id"]) if pending.get("kind") == OUTPUT_KIND else None


async def review_out(db: AsyncSession, user_id: str, review: CvReview) -> CvReviewOut:
    mods = await ModificationRepository(db, user_id).of_review(review.id)
    versions = await VersionRepository(db, user_id).recent(review_ids=[review.id])
    return CvReviewOut.model_validate(
        {
            "id": review.id,
            "posting_id": review.posting_id,
            "status": review.status,
            "session_id": review.session_id,
            "before": before_out(review.before),
            "modifications": [modification_out(m) for m in mods],
            "gap_terms": [str(term) for term in review.keywords_to_gap],
            "report": review.report,
            "versions": [version_out(v) for v in reversed(versions)],
            "waiting_output": await waiting_output(db, user_id, review) is not None,
            "created_at": review.created_at,
        }
    )


async def list_reviews(rt: CvRuntime, user_id: str, posting_id: str | None) -> list[CvReviewOut]:
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        rows = await ReviewRepository(db, user_id).recent(posting_id)
        return [await review_out(db, user_id, row) for row in rows]


async def get_review(rt: CvRuntime, user_id: str, review_id: str) -> CvReviewOut:
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return await review_out(db, user_id, await review_row(db, user_id, review_id))


async def _original_checks(
    rt: CvRuntime, user_id: str, template: CvTemplate, content: CvContent
) -> list[AtsCheck]:
    """Contrôles ATS du PDF d'origine (le document du gabarit) ; aucun s'il n'est plus lisible."""
    stored = await document_file(rt.memory, user_id, template.document_id)
    if stored is None:
        return []
    try:
        layout = await rt.layout.extract_layout(stored.data)
    except AppError as exc:
        logger.warning("CV d'origine illisible : gabarit %s (%s)", template.id, exc.code)
        return []
    return ats_checks(layout, content)


async def _before(
    rt: CvRuntime,
    user_id: str,
    template: CvTemplate,
    profile: MasterProfileData,
    analysis: PostingAnalysis,
) -> Indicators:
    """Indicateurs du CV d'origine : couverture de toutes ses lignes (`backed_only=False`) et
    contrôles ATS de son PDF, lu avec les intitulés copiés de l'original (`sample_content`)."""
    base = base_content(profile, template_order(template.spec))
    lines = content_lines(base)
    cover = coverage(analysis.requirements, analysis.keywords, lines, backed_only=False)
    original = (
        CvContent.model_validate(template.sample_content) if template.sample_content else base
    )
    checks = await _original_checks(rt, user_id, template, original)
    return Indicators(cover, checks)


async def _checked(
    db: AsyncSession, user_id: str, posting_id: str
) -> tuple[PostingAnalysis, MasterProfileData, int, CvTemplate]:
    posting = await get_posting(db, user_id, posting_id)
    if posting.status != "ready" or posting.analysis is None:
        raise posting_not_ready()
    profile_row = await ProfileRepository(db, user_id).latest("validated")
    if profile_row is None:
        raise profile_required()
    template = await TemplateRepository(db, user_id).active()
    if template is None or template.status != "ready" or template.spec is None:
        raise template_required()
    profile = MasterProfileData.model_validate(profile_row.data)
    analysis = PostingAnalysis.model_validate(posting.analysis)
    return analysis, profile, profile_row.version, template


async def _launch(rt: CvRuntime, db: AsyncSession, user_id: str, review: CvReview) -> str:
    try:
        session_id = await rt.launcher.start(
            user_id,
            REVIEW_GRAPH,
            {"review_id": review.id},
            subject_type=REVIEW_SUBJECT,
            subject_id=review.id,
        )
    except BaseException:
        review.status = "failed"
        await db.commit()
        logger.warning("Revue non lancée : utilisateur %s, revue %s", user_id, review.id)
        raise
    review.session_id = session_id
    await db.commit()
    return session_id


async def start_review(rt: CvRuntime, user_id: str, posting_id: str) -> ReviewStarted:
    """Voir l'en-tête du module : 404 `posting_not_found`, 409 `posting_not_ready`,
    `profile_required`, `template_required`, `review_in_progress`."""
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        analysis, profile, version, template = await _checked(db, user_id, posting_id)
        if (current := await ReviewRepository(db, user_id).open_on(posting_id)) is not None:
            raise review_in_progress(current.id)
        before = await _before(rt, user_id, template, profile, analysis)
        review = await ReviewRepository(db, user_id).add(
            posting_id=posting_id,
            template_id=template.id,
            profile_version=version,
            status="running",
            before=indicators_json(before),
        )
        await db.commit()  # le parcours relit la revue dans sa propre session
        session_id = await _launch(rt, db, user_id, review)
        review_id = review.id
    logger.info(
        "Revue lancée : utilisateur %s, revue %s, offre %s, profil v%d, gabarit %s, session %s",
        user_id,
        review_id,
        posting_id,
        version,
        template.id,
        session_id,
    )
    return ReviewStarted(review_id=review_id, session_id=session_id)
