"""The Moderator during the debate (SPEC 9.3, D85): it opens each round (January's inputs,
catalog at round 1, speaking order) and closes it (early stop if the positions no longer
move). No `interrupt()` here: a replayed node rereads the same inputs and calls the model
again, without writing anything to the database."""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator

from app.agents.nodes.council_rules import (
    DEBATERS,
    MAX_ROUNDS,
    NAMES,
    Debater,
    Node,
    absorb,
    build_catalog,
    goal_vars,
    notes_prompt,
    read_inputs,
    transcript_prompt,
    without_round_commands,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.prose import Prose
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState

AGENT = "moderator"


class RoundPlan(BaseModel):
    order: list[Debater] = Field(min_length=len(DEBATERS), max_length=len(DEBATERS))
    intent: Prose = Field(min_length=1, max_length=200)

    @field_validator("order")
    @classmethod
    def _each_debater_once(cls, order: list[Debater]) -> list[Debater]:
        if len(set(order)) != len(order):
            raise ValueError("each debater speaks once per round, with no duplicate")
        return order


class RoundReview(BaseModel):
    stable: bool
    summary: Prose = Field(min_length=1, max_length=400)


def _round_turns(state: CouncilState, *rounds: int) -> str:
    return transcript_prompt([t for t in state.get("turns", []) if t["round"] in rounds])


async def _ask[T: BaseModel](
    deps: GraphDeps, schema: type[T], prompt: str, trigger: str, *, step: str, intent: str
) -> T:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        schema,
        [SystemMessage(prompt), HumanMessage(trigger)],
        agent=AGENT,
        step=step,
        intent=intent,
    )


def _say(text: str, message_id: str) -> None:
    emit("agent.message", {"message_id": message_id, "text": text}, agent=AGENT)


def make_round_start(deps: GraphDeps) -> Node:
    @node_timeout()
    async def round_start(state: CouncilState) -> CouncilState:
        """January's inputs read (messages -> round notes, commands), then the speaking order.
        `to_proposals` read before a round >= 2: no new round (`turn_index` at the end). Round 1
        always takes place: each debater gives their position (3.1, step 3). On return from the
        choice ("another round"), `another_round` and `to_proposals` sent while waiting are
        ignored; texts and angle stay read."""
        target = state.get("rounds_target") or min(1 + deps.settings.debate_rounds, MAX_ROUNDS)
        read = await read_inputs(deps, state)
        reopened = (state.get("choice") or {}).get("action") == "another_round"
        if reopened:  # return from the choice: the answer already settles the number of rounds
            read = without_round_commands(read)
        update = absorb(state, read, carry=True, target=target)
        if reopened:
            update["choice"] = None
        number = state.get("round", 0) + 1
        if update.get("stop") and number > 1:
            return {**update, "turn_index": len(state.get("order", DEBATERS))}
        catalog = state.get("catalog")
        if catalog is None:
            catalog = await build_catalog(deps, state, agent=AGENT)
        prompt = render_prompt(
            AGENT,
            mode="round",
            **goal_vars(state),
            round=number,
            rounds_target=update.get("rounds_target", target),
            transcript=_round_turns(state, number - 1),
            notes=notes_prompt(update.get("round_notes", [])),
            angle=update.get("angle"),
            debaters=", ".join(f"{slug} ({NAMES[slug]})" for slug in DEBATERS),
        )
        plan = await _ask(
            deps,
            RoundPlan,
            prompt,
            "Set the speaking order for the round.",
            step=f"ordre-{number}",
            intent="setting the speaking order",
        )
        order: list[str] = list(plan.order)
        _say(
            f"Round {number}: {', '.join(NAMES[a] for a in order)}\n{plan.intent}",
            f"{AGENT}-tour-{number}",
        )
        return {**update, "catalog": catalog, "round": number, "order": order, "turn_index": 0}

    return round_start


def make_round_end(deps: GraphDeps) -> Node:
    @node_timeout()
    async def round_end(state: CouncilState) -> CouncilState:
        """Inputs that arrived during the round read for the next; from round 2 to the second to
        last, the Moderator judges whether the positions moved (stable: end of the debate) and
        summarizes."""
        number = state.get("round", 1)
        target = state.get("rounds_target", number)
        update = absorb(state, await read_inputs(deps, state), carry=False, target=target)
        if update.get("stop") or not 2 <= number < update.get("rounds_target", target):
            return update
        prompt = render_prompt(
            AGENT,
            mode="review",
            **goal_vars(state),
            round=number,
            transcript=_round_turns(state, number - 1, number),
        )
        review = await _ask(
            deps,
            RoundReview,
            prompt,
            "Review the round.",
            step=f"bilan-{number}",
            intent="summarizing the round",
        )
        _say(review.summary, f"{AGENT}-bilan-{number}")
        return {**update, "stop": review.stable}

    return round_end
