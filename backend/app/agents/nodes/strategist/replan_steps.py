"""The `replan` flow without side effects (D105): question constants, context snapshot, rights
of each option, unknown references, January's answers and texts.

Rights (D105 (2)): "reduce" -> removals only; "deepen" -> additions only; "push back",
"bring forward" and no option -> none, the code's filing is enough and the Strategist only
writes a summary. The model only receives the schema of its rights (`schema_for`), and `to_draft`
empties everything else."""

import json
from dataclasses import asdict
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.agents.tools.program_port import BudgetView
from app.agents.tools.replan_port import (
    ModuleRef,
    PreviewSaved,
    ReplanAdds,
    ReplanContext,
    ReplanDraft,
    ReplanDrops,
    ReplanSummary,
    ReviewView,
    TaskRef,
)
from app.agents.tools.study_schema import ReplanOption

AGENT = "strategist"
REPLAN_REQUEST = "Propose an updated study plan."
REPLAN_OPTION = "replan_option"
ACCEPT_REPLAN = "accept_replan"
OPTION_LABELS: dict[str, str] = {
    "reduce_scope": "Reduce the scope",
    "push_deadline": "Move the deadline",
    "advance": "Bring work forward",
    "deepen": "Study in more depth",
}
OPTION_QUESTIONS = {
    "late_twice": "You're two weeks behind. How would you like to adjust the plan?",
    "ahead": "You're ahead of schedule. How would you like to adjust the plan?",
}
ACCEPT_INTERRUPT: dict[str, Any] = {
    "kind": ACCEPT_REPLAN,
    "question": "Review the changes. Would you like to accept the new plan?",
    "options": [
        {"value": "accept", "label": "Accept the new plan"},
        {"value": "refuse", "label": "Keep the current plan"},
    ],
    "fields": [{"id": "note", "label": "What should change in the next proposal?"}],
}
STALE_NOTE = "The program changed. A new proposal will use the updated plan."
EMPTY_NOTE_HINT = "Describe what you'd like to change."
EMPTY_TEXT = "Your current plan fits your time budget. No changes are needed."
GAP_EMPTY_TEXT = (
    "No tasks could be added for these skills. Select Add to schedule to request another proposal."
)
IMPOSSIBLE_TEXT = "This week's time budget is too small for a practice task and quiz."
FINISHED_TEXT = "You've completed the program. There are no weeks left to reschedule."
REFUSED_TEXT = "You declined the proposal and kept your current plan."
REASONS = {"weekly_review": "Weekly review", "gap": "Skills from job postings"}
MAX_NOTE_CHARS = 2000
MAX_REASON_CHARS = 300


# --- Context snapshot (graph state) -------------------------------------------------------------


def as_json(value: ReplanContext | PreviewSaved) -> dict[str, Any]:
    """A port datum as JSON (ISO dates), for the graph state. `ReplanContext`: it is the
    snapshot of the references, reread by `context_from_state`."""
    return dict(json.loads(json.dumps(asdict(value), default=str)))


def context_from_state(data: dict[str, Any]) -> ReplanContext:
    review = data["review"]
    deadline = data["deadline"]
    return ReplanContext(
        program_id=data["program_id"],
        title=data["title"],
        goal=data["goal"],
        deadline=date.fromisoformat(deadline) if deadline else None,
        budget=BudgetView(**data["budget"]),
        review=None
        if review is None
        else ReviewView(**{**review, "week_start": date.fromisoformat(review["week_start"])}),
        options=tuple(data["options"]),
        modules=[ModuleRef(**m) for m in data["modules"]],
        tasks=[TaskRef.from_checkpoint(t) for t in data["tasks"]],
        week_cap_override=data["week_cap_override"],
        message=data["message"],
        skills=tuple(data.get("skills", ())),  # absent from a snapshot from before D123
    )


# --- Option rights and references ---------------------------------------------------------------


def schema_for(option: ReplanOption | None) -> type[ReplanSummary]:
    if option == "reduce_scope":
        return ReplanDrops
    if option == "deepen":
        return ReplanAdds
    return ReplanSummary


def to_draft(found: ReplanSummary, option: ReplanOption | None) -> ReplanDraft:
    """The complete draft, emptied of what the option does not allow (duplicates removed)."""
    drop = list(dict.fromkeys(getattr(found, "drop", []))) if option == "reduce_scope" else []
    add = list(getattr(found, "add", [])) if option == "deepen" else []
    return ReplanDraft(summary=found.summary, drop=drop, add=add)


def unknown_refs(draft: ReplanDraft, ctx: ReplanContext) -> list[str]:
    """References absent from the snapshot, in order (no duplicates)."""
    tasks = {t.ref for t in ctx.tasks}
    modules = {m.ref for m in ctx.modules}
    found = [ref for ref in draft.drop if ref not in tasks]
    found += [task.module for task in draft.add if task.module not in modules]
    return list(dict.fromkeys(found))


def without_unknown(draft: ReplanDraft, ctx: ReplanContext) -> ReplanDraft:
    unknown = set(unknown_refs(draft, ctx))
    return ReplanDraft(
        summary=draft.summary,
        drop=[ref for ref in draft.drop if ref not in unknown],
        add=[task for task in draft.add if task.module not in unknown],
    )


def unknown_text(unknown: list[str]) -> str:
    return (
        f"The plan has no entries for {', '.join(unknown)}. Answer again using only listed "
        "references. Tasks start with `t` and modules with `m`."
    )


# --- January's answers --------------------------------------------------------------------------


def option_payload(ctx: ReplanContext) -> dict[str, Any]:
    state = ctx.review.state if ctx.review else ""
    return {
        "kind": REPLAN_OPTION,
        "question": OPTION_QUESTIONS.get(state, "How would you like to adjust the plan?"),
        "options": [{"value": o, "label": OPTION_LABELS[o]} for o in ctx.options],
    }


def parse_option(value: Any, options: list[str]) -> str | None:
    """The value of an offered option (`"reduce_scope"` or `{"option": ...}`); otherwise `None`."""
    if isinstance(value, dict):
        value = value.get("option")
    return value if isinstance(value, str) and value in options else None


class AcceptAnswer(BaseModel):
    action: Literal["accept", "refuse", "revise"]
    note: str = Field(default="", max_length=MAX_NOTE_CHARS)


def parse_accept(value: Any) -> AcceptAnswer | None:
    """`"accept"`, `"refuse"`, `{"action": ..., "note": ...}` or `{"answers": {"note": ...}}`
    (revision). A revision requires a non-empty note (cut at 2,000 characters, never lost).
    Any other shape: `None` (the question is asked again)."""
    if value in ("accept", "refuse"):
        return AcceptAnswer(action=value)
    if not isinstance(value, dict):
        return None
    if "action" not in value and isinstance(value.get("answers"), dict):
        value = {"action": "revise", "note": value["answers"].get("note")}
    note = value.get("note")
    note = note.strip()[:MAX_NOTE_CHARS] if isinstance(note, str) else ""
    try:
        answer = AcceptAnswer.model_validate({"action": value.get("action"), "note": note})
    except ValidationError:
        return None
    if answer.action == "revise":
        return answer if answer.note else None
    return AcceptAnswer(action=answer.action)


def empty_note(value: Any) -> bool:
    """A request for another proposal with nothing written (D106): the question comes back with
    `EMPTY_NOTE_HINT`, never silently."""
    if not isinstance(value, dict):
        return False
    if "action" not in value and isinstance(value.get("answers"), dict):
        value = {"action": "revise", "note": value["answers"].get("note")}
    note = value.get("note")
    return value.get("action") == "revise" and not (isinstance(note, str) and note.strip())


def accept_payload(hint: str) -> dict[str, Any]:
    """The acceptance question, preceded by the hint when it is asked again."""
    if not hint:
        return ACCEPT_INTERRUPT
    return {**ACCEPT_INTERRUPT, "question": f"{hint} {ACCEPT_INTERRUPT['question']}"}


# --- Texts --------------------------------------------------------------------------------------


def reason_text(state_trigger: str, option: str | None, revision: int, note: str) -> str:
    parts = [REASONS.get(state_trigger, "Message from January")]
    if option:
        parts.append(OPTION_LABELS[option])
    if revision:
        parts.append(f"Proposal {revision + 1}")
    text = " · ".join(parts)
    return (f"{text} — {note}" if note else text)[:MAX_REASON_CHARS]


def preview_text(summary: str, saved: PreviewSaved) -> str:
    """The Strategist's summary, then the figures of the proposal filed by the code."""
    facts = (
        f"The proposal removes {saved.removed}, adds {saved.added}, and moves {saved.moved} "
        f"tasks. The plan goes from {saved.weeks_before} to {saved.weeks_after} weeks, using up "
        "to 85% of your time budget each week."
    )
    if saved.kept:
        facts += f" Skipped removals ({saved.kept}) preserve a practice task and quiz each week."
    return f"{summary}\n\n{facts}"


def end_text(outcome: str, version: int, trigger: str = "") -> str:
    if outcome == "accepted":
        return f"The new plan is in place (version {version})."
    if outcome == "refused":
        return REFUSED_TEXT
    if outcome == "impossible":
        return IMPOSSIBLE_TEXT
    if outcome == "finished":
        return FINISHED_TEXT
    return GAP_EMPTY_TEXT if trigger == "gap" else EMPTY_TEXT
