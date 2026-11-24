"""API of CV reviews and of January's decisions (SPEC 5.3, 14.2; D130). `POST /cv/reviews`
freezes the validated profile and the active template then starts the `cv_review` flow; the
decisions (`PATCH /cv/modifications/{id}`, `PATCH /cv/reviews/{id}/modifications`) and "Generate
the PDF" (`POST /cv/reviews/{id}/generate`) go through the reviews lock. A 422 names the fields,
never their value."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status

from app.core.deps import CurrentUserDep
from app.features.cv.router.fields import FieldPathsRoute
from app.features.cv.router.profile import CvDep
from app.features.cv.schemas_reviews import (
    BulkDecision,
    BulkResult,
    CvReviewOut,
    ErrorOut,
    GenerateIn,
    GenerateStarted,
    ModificationOut,
    ModificationPatch,
    ReviewStart,
    ReviewStarted,
)
from app.features.cv.service.generate_start import generate
from app.features.cv.service.modifications import decide, decide_many
from app.features.cv.service.reviews import get_review, list_reviews, start_review

router = APIRouter(prefix="/cv", tags=["cv-reviews"], route_class=FieldPathsRoute)

Id = Annotated[str, Path(min_length=1, max_length=36)]


def errors(**by_status: str) -> dict[int | str, dict[str, Any]]:
    """Documented error responses: `{error: {code, message, details}}`, codes listed."""
    return {
        int(code.removeprefix("e")): {"model": ErrorOut, "description": text}
        for code, text in by_status.items()
    }


@router.post(
    "/reviews",
    response_model=ReviewStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=errors(
        e404="`posting_not_found`",
        e409=(
            "`posting_not_ready` (posting not analysed yet), `profile_required` (no validated "
            "profile), `template_required` (no ready active template), `review_in_progress` "
            "(`details.review_id`: the review in progress for this posting)"
        ),
        e503="`engine_unavailable`",
    ),
)
async def post_review(body: ReviewStart, current: CurrentUserDep, rt: CvDep) -> ReviewStarted:
    """Reviews the CV against the posting; the profile (its version) and template are frozen."""
    return await start_review(rt, current.id, body.posting_id)


@router.get("/reviews", response_model=list[CvReviewOut])
async def get_reviews(
    current: CurrentUserDep,
    rt: CvDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[CvReviewOut]:
    """The reviews (of a posting), newest first."""
    return await list_reviews(rt, current.id, posting_id)


@router.get(
    "/reviews/{review_id}",
    response_model=CvReviewOut,
    responses=errors(e404="`review_not_found`"),
)
async def get_one_review(review_id: Id, current: CurrentUserDep, rt: CvDep) -> CvReviewOut:
    return await get_review(rt, current.id, review_id)


@router.patch(
    "/reviews/{review_id}/modifications",
    response_model=BulkResult,
    responses=errors(e404="`review_not_found`", e409="`review_closed`"),
)
async def patch_modifications(
    review_id: Id, body: BulkDecision, current: CurrentUserDep, rt: CvDep
) -> BulkResult:
    """Bulk decision (50 at most); "to confirm" ones are never accepted in bulk: they come
    back in `skipped`, along with unknown identifiers."""
    return await decide_many(rt, current.id, review_id, body)


@router.post(
    "/reviews/{review_id}/generate",
    response_model=GenerateStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=errors(
        e404="`review_not_found`",
        e409=(
            "`review_closed` (review finished or failed), `generation_in_progress` "
            "(`details.version_id`: the version being rendered), `review_not_waiting` (the review "
            'is not waiting on "What do you want now?")'
        ),
        e503="`engine_unavailable`",
    ),
)
async def post_generate(
    review_id: Id, current: CurrentUserDep, rt: CvDep, body: GenerateIn | None = None
) -> GenerateStarted:
    """Creates the version (decisions frozen at the click) and resumes the output question; the
    PDF is followed through `GET /cv/versions/{id}` (status `rendering` then `ready`,
    `pages_exceeded` or `failed`) or through the session's `artifact.ready` event."""
    return await generate(rt, current.id, review_id, body or GenerateIn())


@router.patch(
    "/modifications/{modification_id}",
    response_model=ModificationOut,
    responses=errors(
        e404="`modification_not_found`",
        e409=(
            '`review_closed`, `confirmation_required` ("to confirm" without `confirm: true`), '
            "`fact_not_found` (the targeted fact is no longer in the profile), `profile_conflict`, "
            "`profile_draft_pending` (a profile draft awaits validation: validate it before "
            "confirming a fact)"
        ),
        e422=(
            "`validation_error` (`details.fields`), `keyword_not_in_profile` (the text cites a "
            "posting keyword missing from the profile); never the value received"
        ),
    ),
)
async def patch_modification(
    modification_id: Id, body: ModificationPatch, current: CurrentUserDep, rt: CvDep
) -> ModificationOut:
    """Accepts or refuses; `after`: rewritten text, revalidated (it may stay "to confirm");
    `confirm: true`: accepts a "to confirm" modification, its fact enters the master profile
    (new validated version)."""
    return await decide(rt, current.id, modification_id, body)
