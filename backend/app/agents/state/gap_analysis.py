"""State of the `gap_analysis` graph (D121). The offer, its analysis and the gap live in the
database (port `GapStore`): the state keeps only what passes between nodes. The offer text does
not enter it: `analyze` rereads it through the port."""

from typing import Any, TypedDict


class GapAnalysisState(TypedDict, total=False):
    posting_id: str
    analysis: dict[str, Any] | None  # `PostingAnalysis` as JSON; None: not analyzed yet
    reused: bool  # the analysis was already stored: the Analyst did not redo it
    rejection: str  # reason for refusal without a model call (text too short)
    duplicates: list[dict[str, Any]]  # `DuplicateHit` as JSON (offer analyzed here)
    matches: list[dict[str, Any]]  # `SkillMatch` as JSON, one per need of the offer
    saved: dict[str, Any]  # `GapSaved` as JSON
    summary: str
