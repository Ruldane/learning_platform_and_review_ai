"""One speaking turn of the demo debate, shared by the Proponent and the Critic."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import invoke_agent, message_text
from app.agents.state.demo_debate import DemoDebateState

TRIGGER = "Your turn to speak."


async def play_turn(
    deps: GraphDeps, state: DemoDebateState, *, agent: str, previous: str, intent: str
) -> DemoDebateState:
    """First reads the user's messages received since the last agent (D4), injects them into
    the prompt, calls the model, then returns the state update."""
    fresh = await deps.user_messages_since(state.get("last_message_seq", 0))
    notes = [*state.get("user_notes", []), *(text for _, text in fresh)]
    round_ = state.get("round", 0) + 1
    prompt = render_prompt(
        agent,
        topic=state["topic"],
        round=round_,
        rounds=deps.settings.debate_rounds,
        previous=previous,
        notes=notes,
        angle=state.get("user_choice"),
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(agent).tier, agent=agent)
    reply = await invoke_agent(
        model,
        [SystemMessage(prompt), HumanMessage(TRIGGER)],
        agent=agent,
        step=f"tour-{round_}",
        intent=intent,
    )
    update: DemoDebateState = {"turns": [{"agent": agent, "texte": message_text(reply)}]}
    if fresh:
        update["user_notes"] = [text for _, text in fresh]
        update["last_message_seq"] = fresh[-1][0]
    return update
