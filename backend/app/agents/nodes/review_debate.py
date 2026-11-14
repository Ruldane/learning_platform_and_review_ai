"""Ce que la confrontation dit dans le fil (D129) : le verbe de chaque position et le message de
l'agent. Pur : aucun port, aucun modèle."""

from app.agents.nodes.review_common import LABEL
from app.agents.tools.review_schema import Proposal, Stance

AGENTS = ("ats_reader", "recruiter")
_VERB = {
    1: {"keep": "je garde", "drop": "à retirer", "amend": "autre formulation proposée"},
    2: {"keep": "je maintiens", "drop": "je retire", "amend": "je reformule"},
}


def other(agent: str) -> str:
    return AGENTS[1] if agent == AGENTS[0] else AGENTS[0]


def verb_of(round_no: int, stance: Stance | None, critique: dict[str, str]) -> str:
    """Le verbe du fil : ce qui arrive à la proposition (un auteur muet ne « maintient » rien)."""
    amended = "original" in critique
    if round_no == 2 and stance is None:
        if amended:
            return "sans réponse, l'amendement de l'autre agent reste"
        return "sans réponse, la proposition reste"
    kind = stance.stance if stance else "keep"
    if round_no == 2 and amended and kind == "keep":
        return "je maintiens mon texte d'origine"
    return _VERB[round_no][kind]


def debate_text(
    round_no: int,
    agent: str,
    judged: list[Proposal],
    stances: dict[str, Stance],
    contested: dict[str, dict[str, str]] | None = None,
) -> str:
    """Ce que l'agent dit dans le fil : sa position sur chaque proposition jugée."""
    head = "Tour 2 : je réponds aux objections sur mes propositions."
    if round_no == 1:
        head = f"Tour 1 : mes positions sur les propositions du {LABEL[other(agent)]}."
    lines = [head]
    for p in judged:
        stance = stances.get(p.ref)
        verb = verb_of(round_no, stance, (contested or {}).get(p.ref, {}))
        lines.append(f"- {p.ref} : {verb}." + (f" {stance.reason}" if stance else ""))
    return "\n".join(lines)
