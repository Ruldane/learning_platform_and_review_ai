"""Une prise de parole du débat, commune aux quatre débatteurs (D85, comme `demo_turn`, D53) :
une exécution du nœud = une prise de parole = un point de contrôle.

Le prompt montre les règles, le catalogue numéroté, tous les tours précédents, les messages de
January à traiter et l'angle demandé. Le code tient ensuite les règles de 9.3 qu'il peut
vérifier, avec une seule nouvelle demande : dès le tour 2, nommer un autre débatteur ; le
Sceptique, une ligne « Objection : » ; le premier orateur d'un tour qui suit un message de
January, la nommer. Encore non tenue : la prise de parole est acceptée et l'écart journalisé
(identifiants et codes de règle seulement)."""

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.council_rules import (
    MAX_WORDS,
    NAMES,
    SHORT_WORDS,
    Node,
    catalog_prompt,
    citation_entries,
    goal_vars,
    notes_prompt,
    people_prompt,
    transcript_prompt,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.speech import speak
from app.agents.state.learning_council import CouncilState

TRIGGER = "À toi de parler."
SKEPTIC = "skeptic"
_NAME_PATTERNS = {
    "strategist": re.compile(r"\bStrat[èe]ge\b"),
    "practitioner": re.compile(r"\bPraticien(?:ne)?\b"),
    "scout": re.compile(r"\b[ÉE]claireur\b"),
    "skeptic": re.compile(r"\bSceptique\b"),
}
_OBJECTION = re.compile(r"^\s*[*_]*Objection\s*[*_]*\s*:", re.MULTILINE)
_JANUARY = re.compile(r"\bJanuary\b", re.IGNORECASE)
RULES = {
    "name": "dès le tour 2, réponds nommément à au moins un autre membre du Conseil "
    "(le Stratège, le Praticien, l'Éclaireur ou le Sceptique)",
    "objection": "formule au moins une objection, sur une ligne qui commence par « Objection : »",
    "january": "réponds d'abord à January, en la nommant",
}

logger = logging.getLogger(__name__)


def names_other_debater(text: str, agent: str) -> bool:
    """Vrai si `text` nomme un débatteur autre que `agent` (nom avec majuscule : « le Sceptique »,
    pas l'adjectif « sceptique »)."""
    return any(pattern.search(text) for name, pattern in _NAME_PATTERNS.items() if name != agent)


def broken_rules(text: str, *, agent: str, round: int, answer_january: bool) -> list[str]:
    """Codes des règles de 9.3 non tenues par une prise de parole."""
    broken = []
    if round >= 2 and not names_other_debater(text, agent):
        broken.append("name")
    if agent == SKEPTIC and not _OBJECTION.search(text):
        broken.append("objection")
    if answer_january and not _JANUARY.search(text):
        broken.append("january")
    return broken


def _correction(broken: list[str], max_words: int) -> str:
    rules = "\n".join(f"- {RULES[code]}" for code in broken)
    return (
        f"Ta prise de parole ne respecte pas ces règles du débat :\n{rules}\n"
        f"Reprends-la entièrement en les respectant, {max_words} mots au maximum, en gardant "
        "les citations entre crochets."
    )


async def _to_proposals_pending(deps: GraphDeps, state: CouncilState) -> bool:
    """« Passer aux propositions » arrivé depuis la dernière lecture : regardé sans être consommé
    (la fin du tour lira ces entrées)."""
    fresh = await deps.user_inputs_since(state.get("last_input_seq", 0))
    return any(i.command == "to_proposals" for i in fresh)


def _prompt(state: CouncilState, agent: str, *, first: bool, max_words: int) -> str:
    return render_prompt(
        agent,
        mode="debate",
        **goal_vars(state),
        speaker=NAMES[agent],
        round=state["round"],
        first=first,
        catalog=catalog_prompt(state.get("catalog", [])),
        people=people_prompt(state),
        transcript=transcript_prompt(state.get("turns", [])),
        notes=notes_prompt(state.get("round_notes", [])),
        angle=state.get("angle"),
        max_words=max_words,
    )


def make_turn(deps: GraphDeps) -> Node:
    @node_timeout()
    async def turn(state: CouncilState) -> CouncilState:
        order = state["order"]
        index = state.get("turn_index", 0)
        agent, number = order[index], state["round"]
        if number >= 2 and await _to_proposals_pending(deps, state):
            return {"stop": True, "turn_index": len(order)}
        max_words = SHORT_WORDS if state.get("angle") == "shorter" else MAX_WORDS
        answer_january = index == 0 and bool(state.get("round_notes"))
        model = await deps.models.get_chat_model(deps.user_id, get_agent(agent).tier, agent=agent)

        def revise(text: str) -> str | None:
            broken = broken_rules(text, agent=agent, round=number, answer_january=answer_january)
            return _correction(broken, max_words) if broken else None

        spoken = await speak(
            model,
            [
                SystemMessage(_prompt(state, agent, first=answer_january, max_words=max_words)),
                HumanMessage(TRIGGER),
            ],
            agent=agent,
            step="positions" if number == 1 else f"tour-{number}",
            intent="je donne ma position" if number == 1 else "je réponds au Conseil",
            catalog=citation_entries(state),
            max_words=max_words,
            revise=revise,
        )
        if spoken.revised and (
            still := broken_rules(
                spoken.text, agent=agent, round=number, answer_january=answer_january
            )
        ):
            logger.info(
                "Règles du débat non tenues après relance (%s) : session %s, agent %s, tour %d",
                ",".join(still),
                deps.session_id,
                agent,
                number,
            )
        return {
            "turns": [{"round": number, "agent": agent, "text": spoken.text}],
            "turn_index": index + 1,
        }

    return turn
