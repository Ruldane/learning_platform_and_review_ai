"""State of the `hiring_committee` graph (D147). The context comes from the port (single read);
impressions, turns, votes and summary live in the state (checkpointer) until `save`,
the only write: a finished node is never redone, a given vote is never asked again."""

from typing import Any, TypedDict


class HiringCommitteeState(TypedDict, total=False):
    run_id: str
    context: dict[str, Any]  # `CommitteeContext` as JSON
    # What the personas said, in order: `{"persona", "round", "text"}`; turn 0 is
    # the first impression, turns 1 and 2 the debate.
    spoken: list[dict[str, Any]]
    votes: list[dict[str, Any]]  # `PersonaVote` as JSON, in persona order
    synthesis: dict[str, Any]  # `Synthesis` as JSON: code verdict, objections, changes
    summary: str
