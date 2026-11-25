"""Port for reviewing a CV against an offer (SPEC 5.3, F9, D129). `app.agents` imports no
feature (contract 6): it describes here what the `cv_review` graph needs; the `cv` feature
implements it (`AgentCvReviewStore`, task 6.14).

The master profile, the CV and the offer text are personal or untrusted data
(17.2, 17.4): never logged, neither here nor by the implementation.

Each write is idempotent, so that a node replayed after a stop (SPEC 9.4) writes nothing
plus :
- `save_company`: by `(user, company key, session)`;
- `save_proposals`: `(review, reference)` unique; the review moves to `proposed`;
- `render_version`: a version already rendered is reread, never rendered twice;
- `close`: the review moves to `done`, once only.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.prose import ShortenToMax
from app.agents.tools.cv_indicators import Indicators
from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.agents.tools.cv_validator import Verdict
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import CompanyBrief, Proposal
from app.core.errors import AppError
from app.db.models.career import VersionStatus

BRIEF_MAX_AGE_DAYS = 30  # an older company record is redone by the Scout
ATS_UPDATES_MAX_AGE_DAYS = 60  # beyond that, the last ATS refresh is no longer shown
ATS_UPDATES_MAX = 3

OutputChoice = Literal["report", "pdf", "finish"]
# Free text read by January (shortcut, never refused, D97).
Note = Annotated[str, Field(max_length=300), ShortenToMax()]


@dataclass(frozen=True)
class AtsUpdate:
    """A "kept" source from the last web refresh on the ATS (P14): text coming from the
    web, hence untrusted (17.4); `published`: its date if the page gives it."""

    title: str
    url: str
    summary: str
    published: str | None


@dataclass(frozen=True)
class ReviewContext:
    """What the review reads: the offer (stored analysis or `None`), the validated profile frozen in
    the review, the composed original CV (`base_content`, order of the template's sections), the
    indicators before, the company and its record of less than `BRIEF_MAX_AGE_DAYS` days (otherwise
    `None`) with the ATS already spotted for it (`company_ats`; a reused record would
    otherwise lose the ATS read from its pages). `ats_updates`: the sources kept from the last
    `ats_refresh` session finished less than `ATS_UPDATES_MAX_AGE_DAYS` days ago, 3 at most."""

    review_id: str
    posting_id: str
    analysis: PostingAnalysis | None
    posting_text: str
    posting_urls: list[str]
    profile: MasterProfileData
    base: CvContent
    before: Indicators
    company: str | None
    company_brief: CompanyBrief | None
    company_ats: str | None = None
    ats_updates: list[AtsUpdate] = field(default_factory=list)


@dataclass(frozen=True)
class VersionOutcome:
    """A rendered version: `pages_exceeded` when the targeted CV keeps more pages than the original
    (`original_page_count`, deviation from the plan: the sentence said to January cites it)."""

    version_id: str
    status: VersionStatus
    page_count: int | None
    filename: str
    original_page_count: int = 1


class ReviewReport(BaseModel):
    """The review report: detected ATS and its notes, company sheet summary, strengths and
    risks seen by the Recruiter, and the posting's knockout criteria. It promises no
    guarantee of passing an ATS."""

    ats: str | None = Field(default=None, max_length=40)
    ats_notes: list[Note] = Field(default_factory=list, max_length=6)
    company_summary: str | None = Field(default=None, max_length=800)
    strengths: list[Note] = Field(default_factory=list, max_length=5)
    risks: list[Note] = Field(default_factory=list, max_length=5)
    eliminatory: list[Annotated[str, Field(max_length=300)]] = Field(
        default_factory=list, max_length=10
    )


class CvReviewStore(Protocol):
    async def context(self, user_id: str, review_id: str) -> ReviewContext:
        """January's review; 404 `review_not_found` if it is not theirs. Read-only."""
        ...

    async def save_company(
        self,
        user_id: str,
        session_id: str,
        name: str,
        brief: CompanyBrief,
        sources: Sequence[str],
        ats: str | None,
    ) -> None:
        """The company record (`companies`, `refreshed_at`), attached to the review; idempotent
        per `(user, company key, session)`."""
        ...

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        review_id: str,
        items: Sequence[tuple[Proposal, Verdict]],
        gap_terms: Sequence[str],
        report: ReviewReport,
    ) -> int:
        """The modifications (`proposed` if the verdict is `ok`, `to_confirm` otherwise, with its
        `blocks`), the keywords that went to the gap and the report; the review moves to
        `proposed`. Idempotent: `(review, reference)` unique. Returns the number of modifications
        stored for the review."""
        ...

    async def render_version(self, user_id: str, version_id: str) -> VersionOutcome:
        """Returns the version created by the route (6.14); idempotent: already rendered, reread."""
        ...

    async def close(self, user_id: str, review_id: str) -> None:
        """The review moves to `done`; idempotent."""
        ...


def cv_review_unavailable() -> AppError:
    return AppError("cv_review_unavailable", "CV reviews are unavailable in this runtime.", 503)


class _NoCvReview:
    """Engine default value (tests, starts without the feature)."""

    async def context(self, user_id: str, review_id: str) -> ReviewContext:
        raise cv_review_unavailable()

    async def save_company(
        self,
        user_id: str,
        session_id: str,
        name: str,
        brief: CompanyBrief,
        sources: Sequence[str],
        ats: str | None,
    ) -> None:
        raise cv_review_unavailable()

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        review_id: str,
        items: Sequence[tuple[Proposal, Verdict]],
        gap_terms: Sequence[str],
        report: ReviewReport,
    ) -> int:
        raise cv_review_unavailable()

    async def render_version(self, user_id: str, version_id: str) -> VersionOutcome:
        raise cv_review_unavailable()

    async def close(self, user_id: str, review_id: str) -> None:
        raise cv_review_unavailable()


NO_CV_REVIEW: CvReviewStore = _NoCvReview()
