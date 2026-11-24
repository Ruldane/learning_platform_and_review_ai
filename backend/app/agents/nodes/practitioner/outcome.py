"""Serialize project evaluations and summarize their results from stored counts (P3)."""

from typing import Any

from pydantic import TypeAdapter

from app.agents.tools.project_port import ReviewOutcome
from app.agents.tools.project_schema import NOT_ASSESSED, unmet_count

_ADAPTER = TypeAdapter(ReviewOutcome)
_NOT_ASSESSED_COMMENTS = frozenset({NOT_ASSESSED, "Critère non évalué."})


def to_state(outcome: ReviewOutcome) -> dict[str, Any]:
    return dict(_ADAPTER.dump_python(outcome, mode="json"))


def from_state(data: dict[str, Any]) -> ReviewOutcome:
    return _ADAPTER.validate_python(data)


def _plural(number: int, one: str, many: str) -> str:
    return f"{number} {one if number == 1 else many}"


def summary_text(outcome: ReviewOutcome) -> str:
    """Describe the outcome with counts and omit submission content."""
    if outcome.verdict == "validated":
        drafts = outcome.drafts or []
        if not drafts:
            return "Project approved. Drafts unavailable."
        ready = sum(draft.status == "ready" for draft in drafts)
        text = f"Project approved. {_plural(ready, 'draft ready', 'drafts ready')}"
        return f"{text}, {len(drafts) - ready} to review." if len(drafts) > ready else f"{text}."
    total = len(outcome.results)
    if all(result.comment in _NOT_ASSESSED_COMMENTS for result in outcome.results):
        return "Project needs revision. The submission could not be assessed."
    unmet = unmet_count(total, outcome.results)
    if unmet == 0:
        return "Project needs revision. The assessment does not match the brief."
    return f"Project needs revision. Unmet criteria: {unmet} of {total}."
