"""January's decisions on the modifications of a review (SPEC 5.3 step 7, 5.5; D128, D130).

- Refuse: always possible while the review is not finished.
- Accept: a "to confirm" modification (`blocks` not empty: figure, tool, title or name absent
  from the profile) is only accepted with `confirm: true`, one by one; the fact then enters the
  master profile (new validated version, `profile_facts`) and `blocks` is emptied.
- Text rewritten by January (`after`, rewrite or addition only): re-validated against the
  profile frozen in the review; it may become "to confirm"; a posting keyword absent from the
  profile never enters the CV (422 `keyword_not_in_profile`, without echo).
- As a group: the "to confirm" ones are never accepted (skipped and returned in `skipped`).

After "Finish" (or the review's failure): 409 `review_closed`. Under the reviews lock: a click
on "Generate" freezes the decisions of a precise instant. Logs: ids only."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_validator import validate
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.career import CvModification, CvReview
from app.features.cv.repository import ModificationRepository
from app.features.cv.schemas_reviews import (
    BulkDecision,
    BulkResult,
    ModificationOut,
    ModificationPatch,
)
from app.features.cv.service.generate_start import as_proposal
from app.features.cv.service.profile_facts import confirm_fact, invalid_after
from app.features.cv.service.review_data import (
    modification_not_found,
    modification_out,
    review_closed,
)
from app.features.cv.service.review_store import frozen_base, review_row
from app.features.cv.service.reviews import settle
from app.features.cv.service.runtime import CvRuntime
from app.features.postings.service.queries import get_posting

logger = logging.getLogger(__name__)

EDITABLE = ("rewrite", "add")


def confirmation_required() -> AppError:
    return AppError(
        "confirmation_required",
        "Confirm that the fact missing from your profile is true before accepting this edit.",
        409,
    )


def keyword_not_in_profile() -> AppError:
    return AppError(
        "keyword_not_in_profile",
        "This edit contains a posting keyword missing from your profile. "
        "It stays in the skill gap.",
        422,
        {"fields": ["after"]},
    )


def needs_confirmation(row: CvModification) -> bool:
    return row.status == "to_confirm" or bool(row.blocks)


async def _open_review(db: AsyncSession, user_id: str, review_id: str) -> CvReview:
    review = await review_row(db, user_id, review_id)
    if review.status != "proposed":
        raise review_closed()
    return review


async def _revalidate(
    db: AsyncSession, user_id: str, review: CvReview, row: CvModification, after: str
) -> bool:
    """January's text replaces `after`, re-validated against the frozen profile (D128); true
    if it is "to confirm"."""
    if row.action not in EDITABLE:
        raise invalid_after()
    profile, _ = await frozen_base(db, user_id, review)
    posting = await get_posting(db, user_id, review.posting_id)
    analysis = PostingAnalysis.model_validate(posting.analysis)
    candidate = as_proposal(row).model_copy(update={"after": after})
    verdict = validate(candidate, profile, analysis)
    if verdict.status == "to_gap":
        raise keyword_not_in_profile()
    row.after, row.blocks = after, list(verdict.blocks)
    return verdict.status == "to_confirm"


async def _accept(
    rt: CvRuntime, db: AsyncSession, user_id: str, row: CvModification, body: ModificationPatch
) -> int | None:
    """Accepts, or keeps "to confirm", a rewritten text without confirmation; returns the
    profile version written by a confirmation."""
    review = await _open_review(db, user_id, row.review_id)
    if body.after is not None:
        needs = await _revalidate(db, user_id, review, row, body.after.strip())
    else:
        needs = needs_confirmation(row)
    if needs and not body.confirm:
        if body.after is None:
            raise confirmation_required()
        row.status = "to_confirm"  # rewritten text: kept, to confirm one by one
        return None
    confirmed = await confirm_fact(rt, user_id, row.target, row.after) if needs else None
    row.status, row.blocks = "accepted", []
    return confirmed


async def decide(
    rt: CvRuntime, user_id: str, modification_id: str, body: ModificationPatch
) -> ModificationOut:
    """See the module header; returns the modification as it is stored."""
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = await ModificationRepository(db, user_id).get(modification_id)
        if row is None:
            raise modification_not_found()
        if body.status == "accepted":
            confirmed = await _accept(rt, db, user_id, row, body)
        else:
            await _open_review(db, user_id, row.review_id)
            row.status, confirmed = "refused", None
        row.decided_at = rt.now()
        await db.commit()
        out = modification_out(row)
    logger.info(
        "Decision: user %s, modification %s, status %s, profile confirmed %s",
        user_id,
        modification_id,
        out.status,
        confirmed,
    )
    return out


async def decide_many(
    rt: CvRuntime, user_id: str, review_id: str, body: BulkDecision
) -> BulkResult:
    """Group decision; the "to confirm" ones are never accepted as a group."""
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        await _open_review(db, user_id, review_id)
        rows = {
            row.id: row for row in await ModificationRepository(db, user_id).of_review(review_id)
        }
        skipped: list[str] = []
        updated = 0
        for mod_id in dict.fromkeys(body.ids):
            row = rows.get(mod_id)
            if row is None or (body.status == "accepted" and needs_confirmation(row)):
                skipped.append(mod_id)
                continue
            row.status, row.decided_at = body.status, rt.now()
            updated += 1
        await db.commit()
    logger.info(
        "Group decisions: user %s, review %s, %d applied, %d skipped",
        user_id,
        review_id,
        updated,
        len(skipped),
    )
    return BulkResult(updated=updated, skipped=skipped)
