"""Proponent node: opens the debate, then answers the Critic."""

from app.agents.nodes.demo_turn import play_turn
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.demo_debate import DebateNode, DemoDebateState

AGENT = "demo_proponent"


def make_proponent(deps: GraphDeps) -> DebateNode:
    @node_timeout()
    async def proponent(state: DemoDebateState) -> DemoDebateState:
        last_critic = next(
            (t["texte"] for t in reversed(state.get("turns", [])) if t["agent"] != AGENT), ""
        )
        intent = (
            "I answer the Critic." if last_critic else f"I open the debate on {state['topic']}."
        )
        return await play_turn(deps, state, agent=AGENT, previous=last_critic, intent=intent)

    return proponent
