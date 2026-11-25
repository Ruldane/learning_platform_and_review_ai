"""State of the `replan` graph (D105). The plan is in the database (`ReplanStore`); the state keeps
the context snapshot (the references `t12`, `m3` and their ids, F7), the chosen option, the
Strategist's last draft (to pass to the `preview` node), the proposed version and January's answer.
January."""

from typing import Any, TypedDict


class ReplanState(TypedDict, total=False):
    program_id: str
    trigger: str  # `weekly_review`, `message` or `gap`
    review_entry_id: str | None
    available_minutes: int | None
    message: str | None
    skills: list[str]  # `gap` trigger: skills of the offers to add (D123)
    context: dict[str, Any]  # `ReplanContext` as JSON (ISO dates): the snapshot of the references
    option: str | None  # option chosen by January; None: none (or invalid answer)
    revision: int  # 0: first proposal; +1 at each revision or stale proposal
    note: str  # January's revision note (empty otherwise)
    stale: bool  # the previous proposal was stale (lines changed)
    draft: dict[str, Any]  # `ReplanDraft` as JSON: the last draft, rights applied
    preview: dict[str, Any]  # `PreviewSaved` as JSON: the proposed version
    answer: dict[str, Any] | None  # `AcceptAnswer` as JSON; None: invalid answer
    hint: str  # hint added to the re-asked acceptance question (empty note, D106)
    outcome: str  # `empty`, `impossible`, `finished`, `accepted`, `refused`: the end of the graph
    summary: str
