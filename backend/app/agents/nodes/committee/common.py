"""Ce que les nœuds du comité de recrutement ont en commun (D147) : le type d'un nœud, les
demandes (marqueurs des prompts), le contexte relu depuis l'état et le modèle d'une persona avec
ses deux messages. Journaux : identifiants et nombres seulement, jamais une parole, le CV ni
l'offre."""

import asyncio
from collections.abc import Callable, Coroutine, Sequence
from typing import Any, Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.committee.context import persona_vars
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import PERSONAS, CommitteeContext, Persona
from app.core.played import played_by

IMPRESSION_REQUEST = "Donne ta première impression."
DEBATE_REQUEST = "Prends la parole au débat."
VOTE_REQUEST = "Rends ton vote."
SYNTHESIS_REQUEST = "Rédige la synthèse du comité."
TURN_TIMEOUT_S = 300  # quatre prises de parole de suite, chacune avec ses nouveaux essais (GLM)


class Node(Protocol):
    async def __call__(self, state: HiringCommitteeState) -> HiringCommitteeState: ...


def context_of(state: HiringCommitteeState) -> CommitteeContext:
    return CommitteeContext.model_validate(state["context"])


async def persona_call(
    deps: GraphDeps,
    ctx: CommitteeContext,
    persona: Persona,
    step: str,
    request: str,
    *,
    spoken: Sequence[dict[str, Any]] = (),
    round_number: int = 0,
    addressee: Persona | None = None,
) -> tuple[BaseChatModel, list[BaseMessage]]:
    """Le modèle de la persona (niveau de son agent) et ses messages : son prompt en mode
    `committee` pour l'étape `step` (`impression`, `debate`, `vote`), puis la demande."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(persona).tier, agent=persona)
    variables = persona_vars(ctx, persona, step, spoken, round_number, addressee)
    prompt = render_prompt(persona, **variables)
    return model, [SystemMessage(prompt), HumanMessage(request)]


async def together[T](*calls: Coroutine[Any, Any, T]) -> list[T]:
    """Les appels indépendants d'un nœud, ensemble ; si l'un échoue, les autres sont arrêtés avant
    que l'erreur remonte (aucune parole ni aucun vote ne continue après l'échec du nœud)."""
    tasks = [asyncio.ensure_future(call) for call in calls]
    try:
        return list(await asyncio.gather(*tasks))
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


async def persona_results[T](
    deps: GraphDeps, ask: Callable[[Persona], Coroutine[Any, Any, T]]
) -> list[T]:
    # Une interruption LangGraph par nœud doit être rencontrée dans le même ordre au rejeu.
    if played_by(deps.user_id):
        return [await ask(persona) for persona in PERSONAS]
    return await together(*(ask(persona) for persona in PERSONAS))
