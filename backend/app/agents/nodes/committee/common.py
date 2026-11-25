"""What the hiring committee nodes have in common (D147): the type of a node, the requests
(prompt markers), the context reread from the state and a persona's model with its two
messages. Logs: identifiers and numbers only, never a speech, the CV or the posting."""

import asyncio
from collections.abc import Callable, Coroutine, Mapping, Sequence
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
from app.providers.llm.base import Tier

IMPRESSION_REQUEST = "Give your first impression."
DEBATE_REQUEST = "Respond in the debate."
VOTE_REQUEST = "Cast your vote."
SYNTHESIS_REQUEST = "Summarize the committee's discussion."
TURN_TIMEOUT_S = 300  # four speeches in a row, each with its retries (GLM)


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
    """The persona's model (its agent's tier) and its messages: its prompt in `committee` mode
    for step `step` (`impression`, `debate`, `vote`), then the request."""
    variables = persona_vars(ctx, persona, step, spoken, round_number, addressee)
    return await role_call(deps, persona, persona, request, variables)


async def role_call(
    deps: GraphDeps,
    agent: str,
    prompt_name: str,
    request: str,
    variables: Mapping[str, object],
    *,
    tier: Tier | None = None,
) -> tuple[BaseChatModel, list[BaseMessage]]:
    """Factory and messages of a debate voice."""
    model = await deps.models.get_chat_model(
        deps.user_id, tier or get_agent(agent).tier, agent=agent
    )
    prompt = render_prompt(prompt_name, **variables)
    return model, [SystemMessage(prompt), HumanMessage(request)]


async def together[T](*calls: Coroutine[Any, Any, T]) -> list[T]:
    """A node's independent calls, together; if one fails, the others are stopped before the
    error bubbles up (no speech or vote continues after the node's failure)."""
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
    # One LangGraph interrupt per node must be met in the same order on replay.
    if played_by(deps.user_id):
        return [await ask(persona) for persona in PERSONAS]
    return await together(*(ask(persona) for persona in PERSONAS))
