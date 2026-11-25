"""The committee debate (SPEC F19, D147): two rounds, each persona sees everything that was said.
The speaking order is set by the code (`speaking_order`: that of the personas, shifted by one
rank in round 2), never by a model; the Moderator only speaks at the synthesis.

The debate rules are the Council's (SPEC 9.3, `council_rules`): 150 words at most (cut by the
code in `speak`) and, from round 2, answer at least one other by name. To hold the call budget
(17 at most), the rule is not requested again from the model: the prompt designates who to
answer (the last to have spoken), and a rule not met is accepted then logged (identifiers and
rule code only, like the Council after its retry)."""

import logging
import re
from typing import Any

from app.agents.nodes.committee.common import (
    DEBATE_REQUEST,
    TURN_TIMEOUT_S,
    Node,
    context_of,
    persona_call,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.speech import speak
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import MAX_WORDS, Persona, speaking_order

_NAME_PATTERNS: dict[str, re.Pattern[str]] = {
    "ats_reader": re.compile(r"\b(?:ATS reader|Lecteur ATS|filtre machine)\b", re.IGNORECASE),
    "recruiter": re.compile(r"\b(?:Recruiter|Recruteu(?:r|se))\b"),
    "manager": re.compile(r"\bManager\b"),
    "colleague": re.compile(r"\b(?:Future colleague|Futur(?:e)? coll[èe]gue|Coll[èe]gue)\b"),
}

logger = logging.getLogger(__name__)


def names_other_persona(text: str, persona: str) -> bool:
    """True if `text` names another committee persona (name with a capital: "the Manager")."""
    return any(p.search(text) for name, p in _NAME_PATTERNS.items() if name != persona)


def addressee_of(spoken: list[dict[str, Any]], persona: Persona) -> Persona | None:
    """Who to answer: the last persona to have spoken, other than `persona`."""
    for item in reversed(spoken):
        if item["persona"] != persona:
            return item["persona"]  # type: ignore[no-any-return]
    return None


def make_round(deps: GraphDeps, number: int) -> Node:
    @node_timeout(TURN_TIMEOUT_S)
    async def debate_round(state: HiringCommitteeState) -> HiringCommitteeState:
        """Round `number`: four speeches in a row, each after the previous ones."""
        ctx = context_of(state)
        spoken = list(state["spoken"])
        for persona in speaking_order(number):
            addressee = addressee_of(spoken, persona) if number >= 2 else None
            model, messages = await persona_call(
                deps,
                ctx,
                persona,
                "debate",
                DEBATE_REQUEST,
                spoken=spoken,
                round_number=number,
                addressee=addressee,
            )
            said = await speak(
                model,
                messages,
                agent=persona,
                step=f"tour-{number}",
                intent="responding to the committee" if number >= 2 else "stating my position",
                catalog=[],
                max_words=MAX_WORDS,
            )
            if number >= 2 and not names_other_persona(said.text, persona):
                logger.info(
                    "Debate rule not met (name): session %s, persona %s, round %d",
                    deps.session_id,
                    persona,
                    number,
                )
            spoken.append({"persona": persona, "round": number, "text": said.text})
        return {"spoken": spoken}

    return debate_round
