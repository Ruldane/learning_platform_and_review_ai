"""State of the `cv_review` graph (D129). The offer, profile, original CV and review live in
the database (port `CvReviewStore`): each node rereads the context through `context` (read-only),
and the state keeps only what passes between nodes. The offer text does not enter it. Proposals
(CV texts) are personal data: the state keeps them for the duration of the
session (checkpoints), never a log."""

from typing import Any, TypedDict


class CvReviewState(TypedDict, total=False):
    review_id: str
    posting_id: str
    analysis: dict[str, Any] | None  # `PostingAnalysis` as JSON; None: not analyzed yet
    reused: bool  # written by the Analyst's `analyze` node (6.5)
    rejection: str  # idem : texte trop court
    duplicates: list[dict[str, Any]]  # written by the Analyst's `save_analysis` (unused)
    company: str | None  # company name (offer), `None`: unknown
    company_brief: dict[str, Any] | None  # `CompanyBrief` as JSON
    ats: str | None  # ATS spotted from a link's domain
    ats_notes: list[str]  # notes from the ATS reader (report)
    strengths: list[str]  # strengths seen by the Recruiter (report)
    risks: list[str]  # risks seen by the Recruiter (report)
    proposals: list[dict[str, Any]]  # `Proposal` as JSON, current text (amendments included)
    # ref. -> {stance, reason[, original]} from the other agent in turn 1 (original: before `amend`)
    contested: dict[str, dict[str, str]]
    removed: list[str]  # refs removed in turn 2: the author said `drop`
    items: list[dict[str, Any]]  # {proposal, status, blocks} after the validator
    # offer keywords that the cited facts do not carry: to back with a fact or to acquire
    gap_terms: list[str]
    saved: int  # changes stored
    output: dict[str, Any] | None  # parsed answer to the `cv_output` question
    summary: str
