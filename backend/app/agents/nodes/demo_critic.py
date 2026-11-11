"""Nœud du Critique : répond nommément au Défenseur, puis clôt le tour."""

from app.agents.nodes.demo_turn import play_turn
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.demo_debate import DebateNode, DemoDebateState

AGENT = "demo_critic"


def make_critic(deps: GraphDeps) -> DebateNode:
    @node_timeout()
    async def critic(state: DemoDebateState) -> DemoDebateState:
        last_proponent = next(
            (t["texte"] for t in reversed(state.get("turns", [])) if t["agent"] != AGENT), ""
        )
        update = await play_turn(
            deps,
            state,
            agent=AGENT,
            previous=last_proponent,
            intent="Je cherche la limite de l'argument du Défenseur.",
        )
        update["round"] = state.get("round", 0) + 1
        return update

    return critic
