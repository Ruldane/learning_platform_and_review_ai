"""State of the `program_builder` graph (D86). The plan itself is in the database (port
`ProgramStore`), not here: the state only keeps the prompt context, the Strategist's last draft
(to pass to the `save` node), the references of the stored version and January's answer."""

from typing import Any, TypedDict


class ProgramState(TypedDict, total=False):
    goal_id: str
    proposal_ids: list[str]  # one proposal chosen, or two for a mix
    start_date: str | None  # ISO; `None`: next Monday (chosen by the port)
    plan_vars: dict[str, Any]  # variables of the `plan` prompt, taken from the port context
    revision: int  # 0: first version; +1 at each revision requested by January
    note: str  # January's revision note (empty for the first version)
    draft: dict[str, Any]  # `PlanDraft` as JSON: the Strategist's last draft
    saved: dict[str, Any]  # `DraftSaved` as JSON: the stored version
    validation: dict[str, Any] | None  # `ValidationAnswer` as JSON; None: invalid answer
    summary: str
