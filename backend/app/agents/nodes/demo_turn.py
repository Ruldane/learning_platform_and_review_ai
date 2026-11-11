"""Un tour de parole du débat de démonstration, commun au Défenseur et au Critique."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import invoke_agent, message_text
from app.agents.state.demo_debate import DemoDebateState

TRIGGER = "À toi de parler."


async def play_turn(
    deps: GraphDeps, state: DemoDebateState, *, agent: str, previous: str, intent: str
) -> DemoDebateState:
    """Lit d'abord les messages de l'utilisatrice arrivés depuis le dernier agent (D4), les
    injecte dans le prompt, appelle le modèle, puis renvoie la mise à jour de l'état."""
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
