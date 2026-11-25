"""The choice of the path (SPEC 3.1, step 6; stop point no. 2, D85): a path from the last batch,
a mix of two, or a new round of debate.

`ask_choice` only does `interrupt()` then parses the answer (pure): nothing before the stop
(SPEC 9.4). An invalid answer asks the question again; a new round sends back to the debate with
one more round. `finalize` records the choice then starts the `program_builder` session itself
(port, idempotent: only one per goal), whatever the path of the answer (generic resume or Council
route)."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from langgraph.types import interrupt
from pydantic import BaseModel, Field, ValidationError

from app.agents.nodes.council_rules import MAX_ROUNDS, Node
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.learning_council import CouncilState
from app.agents.tools.council_port import Choice

AGENT = "moderator"
ANOTHER_ROUND: Literal["another_round"] = "another_round"
CHOICE_QUESTION = "Choose a path in the Proposals tab, mix two of them, or ask for another round."
ANOTHER_ROUND_OPTION = {"value": ANOTHER_ROUND, "label": "Ask for another round"}

logger = logging.getLogger(__name__)


class ChoiceAnswer(BaseModel):
    action: Literal["choose", "mix", "another_round"]
    proposal_ids: list[str] = Field(default_factory=list, max_length=2)
    start_date: date | None = None


def parse_choice(value: Any, batch_ids: Sequence[str]) -> ChoiceAnswer | None:
    """`"another_round"` (or `{"action": "another_round"}`) -> new round; `choose`: an id of the
    last batch; `mix`: two distinct ids of the batch. Any other shape: `None`."""
    if value == ANOTHER_ROUND:
        return ChoiceAnswer(action=ANOTHER_ROUND)
    if not isinstance(value, dict):
        return None
    try:
        answer = ChoiceAnswer.model_validate(value)
    except ValidationError:
        return None
    ids = answer.proposal_ids
    if answer.action == ANOTHER_ROUND:
        return ChoiceAnswer(action=ANOTHER_ROUND)
    if not all(pid in batch_ids for pid in ids):
        return None
    if answer.action == "choose" and len(ids) == 1:
        return answer
    if answer.action == "mix" and len(ids) == 2 and ids[0] != ids[1]:
        return answer
    return None


def ask_choice(state: CouncilState) -> CouncilState:
    """Stop point no. 2. Nothing before `interrupt()`. At the round cap (8), no more "another
    round" option, and such an answer asks the question again."""
    number = state.get("round", 0)
    at_cap = number >= MAX_ROUNDS
    value = interrupt(
        {
            "kind": "choose_path",
            "question": CHOICE_QUESTION,
            "options": [] if at_cap else [ANOTHER_ROUND_OPTION],
        }
    )
    batch_ids = [p["proposal_id"] for p in state.get("proposals", [])]
    answer = parse_choice(value, batch_ids)
    if answer is None or (answer.action == ANOTHER_ROUND and at_cap):
        return {"choice": None}
    choice = answer.model_dump(mode="json")
    if answer.action == ANOTHER_ROUND:
        return {"choice": choice, "rounds_target": number + 1, "stop": False}
    return {"choice": choice}


def route_choice(state: CouncilState) -> str:
    choice = state.get("choice")
    if choice is None:
        return "ask_choice"
    return "round_start" if choice["action"] == ANOTHER_ROUND else "finalize"


def _summary(choice: Choice, proposals: list[dict[str, Any]]) -> str:
    names = {p["proposal_id"]: p["name"] for p in proposals}
    chosen = [f'"{names.get(pid, pid)}"' for pid in choice.proposal_ids]
    if choice.action == "mix":
        return f"Mix of {chosen[0]} and {chosen[1]}: the Strategist prepares the program."
    return f"Path chosen: {chosen[0]}. The Strategist prepares the program."


def make_finalize(deps: GraphDeps) -> Node:
    @node_timeout()
    async def finalize(state: CouncilState) -> CouncilState:
        """Choice recorded, then program started (two idempotent writes of the port)."""
        answer = ChoiceAnswer.model_validate(state["choice"])
        action: Literal["choose", "mix"] = "mix" if answer.action == "mix" else "choose"
        choice = Choice(action, tuple(answer.proposal_ids), answer.start_date)
        council = deps.ports.council
        await council.record_choice(deps.user_id, deps.session_id, state["goal_id"], choice)
        program = await council.start_program(deps.user_id, state["goal_id"], choice)
        logger.info(
            "Path chosen: session %s, goal %s, program %s",
            deps.session_id,
            state["goal_id"],
            program,
        )
        summary = _summary(choice, state.get("proposals", []))
        emit("agent.message", {"message_id": f"{AGENT}-choix", "text": summary}, agent=AGENT)
        return {"summary": summary}

    return finalize
