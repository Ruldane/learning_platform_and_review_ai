"""State of the `interview` graph (D145). The context comes from the port (single read); the plan,
current question and the exchanges live in the state (checkpointer) until `save`, the only
write: a pending question is therefore resumed without asking the model anything."""

from typing import Any, TypedDict


class InterviewState(TypedDict, total=False):
    interview_id: str
    system_design: bool
    design_submission: dict[str, Any] | None
    design_review: dict[str, Any]
    context: dict[str, Any]  # `InterviewContext` as JSON
    plan: list[dict[str, Any]]  # `PlannedQuestion` as JSON, written once
    position: int  # rank of the current main question (`len(plan)`: all asked)
    current: str  # the text asked to January: the question, or its follow-up
    follow_up_open: bool  # `current` is the follow-up of the current main question
    reply: dict[str, Any] | None  # `{"action": "answer" | "stop", "text"}` ; None : illisible
    exchanges: list[dict[str, Any]]  # `Exchange` as JSON, in plan order
    debrief: dict[str, Any] | None  # `Debrief` as JSON; None: stopped before any answer
    flags: list[str]  # terms of the improved answer that the profile does not state
    cards: list[dict[str, Any]]  # `CardDraft` as JSON, one per missed question
    summary: str
