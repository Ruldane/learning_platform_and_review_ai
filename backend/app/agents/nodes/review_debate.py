"""What the confrontation says in the thread (D129): the verb of each stance and the agent's
message. Pure: no port, no model."""

from app.agents.nodes.review_common import LABEL
from app.agents.tools.review_schema import Proposal, Stance

AGENTS = ("ats_reader", "recruiter")
_VERB = {
    1: {"keep": "I keep it", "drop": "to remove", "amend": "other wording proposed"},
    2: {"keep": "I stand by it", "drop": "I withdraw it", "amend": "I rephrase it"},
}


def other(agent: str) -> str:
    return AGENTS[1] if agent == AGENTS[0] else AGENTS[0]


def verb_of(round_no: int, stance: Stance | None, critique: dict[str, str]) -> str:
    """The thread verb: what happens to the proposal (a silent author does not
    "stand by" anything)."""
    amended = "original" in critique
    if round_no == 2 and stance is None:
        if amended:
            return "no answer, the other agent's amendment stands"
        return "no answer, the proposal stands"
    kind = stance.stance if stance else "keep"
    if round_no == 2 and amended and kind == "keep":
        return "I stand by my original text"
    return _VERB[round_no][kind]


def debate_text(
    round_no: int,
    agent: str,
    judged: list[Proposal],
    stances: dict[str, Stance],
    contested: dict[str, dict[str, str]] | None = None,
) -> str:
    """What the agent says in the thread: its stance on each judged proposal."""
    head = "Round 2: I answer the objections to my proposals."
    if round_no == 1:
        head = f"Round 1: my stances on the {LABEL[other(agent)]}'s proposals."
    lines = [head]
    for p in judged:
        stance = stances.get(p.ref)
        verb = verb_of(round_no, stance, (contested or {}).get(p.ref, {}))
        lines.append(f"- {p.ref}: {verb}." + (f" {stance.reason}" if stance else ""))
    return "\n".join(lines)
