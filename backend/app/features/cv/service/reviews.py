"""CV reviews on the API side (SPEC 5.3, 14.2; D130): launch, list and detail.

`POST /cv/reviews` checks and **freezes** what the review will read: the validated profile (its
version), the active template, the analyzed posting; it computes the before indicators (coverage
of the requirements by the original CV, ATS checks of the original PDF) then launches the
`cv_review` flow. One review in progress per posting (409 `review_in_progress`).

The status follows the outcome of the session (as D126 no. 5): a launched or proposed review
whose session is no longer open (model failure, timeout, cancellation, posting that is not one)
becomes `failed` on the next read, its versions still rendering too, under the reviews lock; a
finished session never resumes: the fix is safe. Logs: ids and numbers only."""

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

OUTPUT_KIND = "cv_output"  # the flow's exit question ("What do you want now?")


def profile_required() -> AppError:
    return AppError(
        "profile_required", "Approve your master profile before starting the CV review.", 409
    )


def template_required() -> AppError:
    return AppError("template_required", "Choose a ready CV template for the tailored CV.", 409)


def posting_not_ready() -> AppError:
    return AppError("posting_not_ready", "Wait for the posting analysis to finish.", 409)


def review_in_progress(review_id: str) -> AppError:
    return AppError(
        "review_in_progress",
        "Finish the CV review already in progress for this posting.",
        409,
        {"review_id": review_id},
    )


async def settle(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    """Reviews in progress without an open session → `failed` (versions rendering too); returns
    the sessions open per review. Sessions read BEFORE the reviews (D97 no. 9). The caller holds
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
        logger.info("Review without session: user %s, review %s", user_id, row.id)
    for version in await VersionRepository(db, user_id).rendering([row.id for row in stale]):
        version.status, version.failure_reason = "failed", RENDER_FAILED
    if stale:
        await db.commit()
    return open_ids


async def waiting_output(db: AsyncSession, user_id: str, review: CvReview) -> str | None:
    """The `interrupt_id` of the exit question if the review's session is waiting on it."""
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
    """ATS checks of the original PDF (the template's document); none if unreadable."""
    stored = await document_file(rt.memory, user_id, template.document_id)
    if stored is None:
        return []
    try:
        layout = await rt.layout.extract_layout(stored.data)
    except AppError as exc:
        logger.warning("Original CV unreadable: template %s (%s)", template.id, exc.code)
        return []
    return ats_checks(layout, content)


async def _before(
    rt: CvRuntime,
    user_id: str,
    template: CvTemplate,
    profile: MasterProfileData,
    analysis: PostingAnalysis,
) -> Indicators:
    """Indicators of the original CV: coverage of all its lines (`backed_only=False`) and ATS
    checks of its PDF, read with the headings copied from the original (`sample_content`)."""
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
        logger.warning("Review not started: user %s, review %s", user_id, review.id)
        raise
    review.session_id = session_id
    await db.commit()
    return session_id


async def start_review(rt: CvRuntime, user_id: str, posting_id: str) -> ReviewStarted:
    """See the module header: 404 `posting_not_found`, 409 `posting_not_ready`,
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
        await db.commit()  # the flow re-reads the review in its own session
        session_id = await _launch(rt, db, user_id, review)
        review_id = review.id
    logger.info(
        "Review started: user %s, review %s, posting %s, profile v%d, template %s, session %s",
        user_id,
        review_id,
        posting_id,
        version,
        template.id,
        session_id,
    )
    return ReviewStarted(review_id=review_id, session_id=session_id)
