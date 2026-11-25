""" "Generate the PDF" (SPEC 5.3; D130): one version per click, decisions frozen at the click,
a single version rendering at a time.

Under the reviews lock: the review must be proposed (409 `review_closed` after "Finish" or a
failure, `review_not_waiting` otherwise), none of its versions rendering (409
`generation_in_progress`) and its session must be waiting for the exit question (409
`review_not_waiting`). The version is created (`rendering`, next number of the posting, content
composed by the code from the modifications **accepted at that instant**, `decisions`: the
decision on each modification, `ignored` if an accepted modification cannot be applied or would
lose a link or a proof from the experience), then the question is resumed with
`{"choice": "pdf", "version_id": …}`. The flow renders the version (`render_version`). A
refused resume removes the version.

Logs: ids and numbers; never the file name nor a CV text."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import Proposal
from app.core.errors import AppError
from app.db.models.career import CvModification, CvReview, CvVersion
from app.features.cv.repository import (
    ModificationRepository,
    ProfileRepository,
    TemplateRepository,
    VersionRepository,
)
from app.features.cv.schemas_reviews import GenerateIn, GenerateStarted
from app.features.cv.service.generate import RENDER_FAILED
from app.features.cv.service.naming import cv_filename
from app.features.cv.service.review_data import posting_title, review_closed
from app.features.cv.service.review_store import frozen_base, review_row
from app.features.cv.service.reviews import settle, waiting_output
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.targeted_content import compose_targeted_cv
from app.features.portfolio.service.links import approved_link
from app.features.postings.service.queries import get_posting

logger = logging.getLogger(__name__)

_NOT_WAITING = ("stale_interrupt", "session_not_resumable", "interrupt_required")


def generation_in_progress(version_id: str) -> AppError:
    return AppError(
        "generation_in_progress",
        "A PDF for this review is being generated. Wait for it to finish.",
        409,
        {"version_id": version_id},
    )


def review_not_waiting() -> AppError:
    return AppError(
        "review_not_waiting",
        "Wait until the CV review asks what you want to do next.",
        409,
    )


def as_proposal(row: CvModification) -> Proposal:
    return Proposal(
        ref=row.ref,
        section=row.section,  # type: ignore[arg-type]  # colonne texte, valeurs de SectionKey
        action=row.action,  # type: ignore[arg-type]  # valeurs de ModificationAction
        target=row.target,
        after=row.after,
        reason=row.reason,
        type=row.type,  # type: ignore[arg-type]  # valeurs de ModificationType
        fact_ids=list(row.fact_ids),
    )


async def _new_version(
    db: AsyncSession,
    user_id: str,
    review: CvReview,
    allow_extra: bool,
    portfolio_origin: str | None,
) -> CvVersion:
    """The version frozen at the click: composed content and decisions of that instant."""
    profile, base = await frozen_base(db, user_id, review)
    posting = await get_posting(db, user_id, review.posting_id)
    analysis = PostingAnalysis.model_validate(posting.analysis) if posting.analysis else None
    company = posting.company or (analysis.company if analysis else None)
    title = (analysis.title if analysis else None) or posting.title
    mods = await ModificationRepository(db, user_id).of_review(review.id)
    accepted = [as_proposal(m) for m in mods if m.status == "accepted"]
    portfolio = await approved_link(db, user_id, "cv", portfolio_origin)
    latest = await ProfileRepository(db, user_id).latest("validated")
    latest_profile = (
        MasterProfileData.model_validate(latest.data)
        if latest is not None and latest.version > review.profile_version
        else None
    )
    applied = compose_targeted_cv(
        base, profile, accepted, analysis, portfolio=portfolio, latest_profile=latest_profile
    )
    decisions = {m.ref: m.status for m in mods} | dict.fromkeys(applied.ignored, "ignored")
    template = await TemplateRepository(db, user_id).get(review.template_id)
    versions = VersionRepository(db, user_id)
    return await versions.add(
        review_id=review.id,
        posting_id=review.posting_id,
        template_id=review.template_id,
        number=await versions.next_number(review.posting_id),
        status="rendering",
        content=applied.content.model_dump(mode="json"),
        decisions=decisions,
        filename=cv_filename(profile.identity.name, company, posting_title(title)),
        original_page_count=template.page_count if template is not None else 1,
        allow_extra_pages=allow_extra,
    )


async def _checked(db: AsyncSession, user_id: str, review_id: str) -> tuple[CvReview, str]:
    """The review, and the `interrupt_id` of the exit question it is waiting on."""
    await settle(db, user_id)
    review = await review_row(db, user_id, review_id)
    if review.status not in ("running", "proposed"):
        raise review_closed()
    interrupt_id = await waiting_output(db, user_id, review)
    rendering = await VersionRepository(db, user_id).rendering([review.id])
    if rendering and interrupt_id is not None:
        # Rendering only runs while the session is `running`: a `rendering` version while the
        # session waits for the exit question stayed there (process died between its recording
        # and the resume); it no longer blocks "Generate" (review 6.14, M-1).
        for stale in rendering:
            stale.status, stale.failure_reason = "failed", RENDER_FAILED
        await db.commit()
        logger.info("Version left rendering: user %s, review %s", user_id, review.id)
        rendering = []
    if rendering:
        raise generation_in_progress(rendering[0].id)
    if interrupt_id is None or review.session_id is None:
        raise review_not_waiting()
    return review, interrupt_id


async def _forget(rt: CvRuntime, user_id: str, version_id: str) -> None:
    async with rt.session_factory() as db:
        await VersionRepository(db, user_id).delete(version_id)
        await db.commit()


async def generate(
    rt: CvRuntime, user_id: str, review_id: str, body: GenerateIn
) -> GenerateStarted:
    """See the module header."""
    async with rt.review_lock(user_id):
        async with rt.session_factory() as db:
            review, interrupt_id = await _checked(db, user_id, review_id)
            version = await _new_version(
                db, user_id, review, body.allow_extra_pages, rt.portfolio_origin()
            )
            await db.commit()  # the flow re-reads the version in its own session
            version_id, session_id, number = version.id, str(review.session_id), version.number
        value = {"choice": "pdf", "version_id": version_id}
        try:
            await rt.resumer.resume(user_id, session_id, interrupt_id, value)
        except BaseException as exc:
            await _forget(rt, user_id, version_id)
            if isinstance(exc, AppError) and exc.code in _NOT_WAITING:
                raise review_not_waiting() from None
            raise
    logger.info(
        "Generation requested: user %s, review %s, version %s (no. %d), session %s",
        user_id,
        review_id,
        version_id,
        number,
        session_id,
    )
    return GenerateStarted(version_id=version_id)
