"""One speech of the debate, common to the four debaters (D85, like `demo_turn`, D53): one run
of the node = one speech = one checkpoint.

The prompt shows the rules, the numbered catalog, all the previous rounds, January's messages to
handle and the requested angle. The code then enforces the 9.3 rules it can check, with a single
new request: from round 2, name another debater; the Skeptic, an "Objection:" line (kept by the
150-word cut, D98); the first speaker of a round that follows a message from January, name her.
Still not met: the speech is accepted and the gap logged (identifiers and rule codes only)."""

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

TRIGGER = "Your turn to speak."
SKEPTIC = "skeptic"
_NAME_PATTERNS = {
    # English names (agents now speak English) and French ones (old threads, user messages).
    "strategist": re.compile(r"\b(?:Strategist|Strat[èe]ge)\b"),
    "practitioner": re.compile(r"\b(?:Practitioner|Praticien(?:ne)?)\b"),
    "scout": re.compile(r"\b(?:Scout|[ÉE]claireur)\b"),
    "skeptic": re.compile(r"\b(?:Skeptic|Sceptique)\b"),
}
# "Objection:", in bold, in a list (`-`, `*`, `1.`, `1)`) or plural, case-insensitive: the line
# is also kept by the 150-word cut (`cap_words(keep=)`, D98).
_OBJECTION = re.compile(
    r"^\s*(?:[-*]\s+|\d+[.)]\s+)?[*_]*Objections?\s*[*_]*\s*:", re.MULTILINE | re.IGNORECASE
)
_JANUARY = re.compile(r"\bJanuary\b", re.IGNORECASE)
RULES = {
    "name": "from round 2, answer at least one other Council member by name "
    "(the Strategist, the Practitioner, the Scout or the Skeptic)",
    "objection": 'make at least one objection, on a line that starts with "Objection:"',
    "january": "answer January first, naming her",
}

logger = logging.getLogger(__name__)


def names_other_debater(text: str, agent: str) -> bool:
    """True if `text` names a debater other than `agent` (name with a capital: "the Skeptic",
    not the adjective "skeptic")."""
    return any(pattern.search(text) for name, pattern in _NAME_PATTERNS.items() if name != agent)


def broken_rules(text: str, *, agent: str, round: int, answer_january: bool) -> list[str]:
    """Codes of the 9.3 rules not met by a speech."""
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
        f"Your speech does not follow these debate rules:\n{rules}\n"
        f"Redo it entirely following them, {max_words} words at most, keeping "
        "the citations in square brackets."
    )


async def _to_proposals_pending(deps: GraphDeps, state: CouncilState) -> bool:
    """ "Move on to proposals" received since the last read: looked at without being consumed
    (the end of the round will read these inputs)."""
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
            intent="stating my position" if number == 1 else "responding to the Council",
            catalog=citation_entries(state),
            max_words=max_words,
            revise=revise,
            keep=_OBJECTION if agent == SKEPTIC else None,
        )
        if spoken.revised and (
            still := broken_rules(
                spoken.text, agent=agent, round=number, answer_january=answer_january
            )
        ):
            logger.info(
                "Debate rules not met after retry (%s): session %s, agent %s, round %d",
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
