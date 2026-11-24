"""Le débat du comité (SPEC F19, D147) : deux tours, chaque persona voit tout ce qui s'est dit.
L'ordre de parole est fixé par le code (`speaking_order` : celui des personas, décalé d'un rang au
tour 2), jamais par un modèle ; le Modérateur ne parle qu'à la synthèse.

Les règles du débat sont celles du Conseil (SPEC 9.3, `council_rules`) : 150 mots au plus (coupe du
code dans `speak`) et, dès le tour 2, répondre nommément à au moins un autre. Pour tenir le budget
d'appels (17 au plus), la règle n'est pas redemandée au modèle : le prompt désigne à qui répondre
(le dernier à avoir parlé), et une règle non tenue est acceptée puis journalisée (identifiants et
code de règle seulement, comme le Conseil après sa relance)."""

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
    """Vrai si `text` nomme une autre persona du comité (nom avec majuscule : « le Manager »)."""
    return any(p.search(text) for name, p in _NAME_PATTERNS.items() if name != persona)


def addressee_of(spoken: list[dict[str, Any]], persona: Persona) -> Persona | None:
    """À qui répondre : la dernière persona à avoir parlé, une autre que `persona`."""
    for item in reversed(spoken):
        if item["persona"] != persona:
            return item["persona"]  # type: ignore[no-any-return]
    return None


def make_round(deps: GraphDeps, number: int) -> Node:
    @node_timeout(TURN_TIMEOUT_S)
    async def debate_round(state: HiringCommitteeState) -> HiringCommitteeState:
        """Le tour `number` : quatre prises de parole de suite, chacune après les précédentes."""
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
                    "Règle du débat non tenue (name) : session %s, persona %s, tour %d",
                    deps.session_id,
                    persona,
                    number,
                )
            spoken.append({"persona": persona, "round": number, "text": said.text})
        return {"spoken": spoken}

    return debate_round
