"""Le Modérateur pendant le débat (SPEC 9.3, D85) : il ouvre chaque tour (entrées de January,
catalogue au tour 1, ordre de parole) et le ferme (arrêt anticipé si les positions ne bougent
plus). Aucun `interrupt()` ici : un nœud rejoué relit les mêmes entrées et rappelle le modèle,
sans rien écrire en base."""

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
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState

AGENT = "moderator"


class RoundPlan(BaseModel):
    order: list[Debater] = Field(min_length=len(DEBATERS), max_length=len(DEBATERS))
    intent: str = Field(min_length=1, max_length=200)

    @field_validator("order")
    @classmethod
    def _each_debater_once(cls, order: list[Debater]) -> list[Debater]:
        if len(set(order)) != len(order):
            raise ValueError("chaque débatteur parle une fois par tour, sans doublon")
        return order


class RoundReview(BaseModel):
    stable: bool
    summary: str = Field(min_length=1, max_length=400)


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
        """Entrées de January lues (messages → notes du tour, commandes), puis l'ordre de parole.
        `to_proposals` lu avant un tour ≥ 2 : pas de nouveau tour (`turn_index` au bout). Le tour 1
        a toujours lieu : chaque débatteur donne sa position (3.1, étape 3). Au retour du choix
        (« autre tour »), `another_round` et `to_proposals` envoyés pendant l'attente sont
        ignorés ; textes et angle restent lus."""
        target = state.get("rounds_target") or min(1 + deps.settings.debate_rounds, MAX_ROUNDS)
        read = await read_inputs(deps, state)
        reopened = (state.get("choice") or {}).get("action") == "another_round"
        if reopened:  # retour du choix : la réponse règle déjà le nombre de tours
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
            "Fixe l'ordre de parole du tour.",
            step=f"ordre-{number}",
            intent="je fixe l'ordre de parole",
        )
        order: list[str] = list(plan.order)
        _say(
            f"Tour {number} : {', '.join(NAMES[a] for a in order)}\n{plan.intent}",
            f"{AGENT}-tour-{number}",
        )
        return {**update, "catalog": catalog, "round": number, "order": order, "turn_index": 0}

    return round_start


def make_round_end(deps: GraphDeps) -> Node:
    @node_timeout()
    async def round_end(state: CouncilState) -> CouncilState:
        """Entrées arrivées pendant le tour lues pour le suivant ; du tour 2 à l'avant-dernier,
        le Modérateur juge si les positions ont bougé (stables : fin du débat) et résume."""
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
            "Fais le point du tour.",
            step=f"bilan-{number}",
            intent="je fais le point du tour",
        )
        _say(review.summary, f"{AGENT}-bilan-{number}")
        return {**update, "stop": review.stable}

    return round_end
