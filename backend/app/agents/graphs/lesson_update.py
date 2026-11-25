"""Draft a private lesson update for review."""

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.lesson_updates_port import SuggestedRevision
from app.providers.llm.limits import with_output_limit

AGENT = "verifier"


class UpdateInput(BaseModel):
    proposal_id: str = Field(min_length=36, max_length=36)


class UpdateState(TypedDict, total=False):
    proposal_id: str
    summary: str


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def review(state: UpdateState) -> UpdateState:
        proposal = state["proposal_id"]
        port = deps.ports.lesson_updates
        context = await port.context(deps.user_id, deps.session_id, proposal)
        if context is not None:
            data = untrusted(json.dumps(context, ensure_ascii=False), "log and examples")
            model = await deps.models.get_chat_model(
                deps.user_id, get_agent(AGENT).tier, agent=AGENT
            )
            result = await structured_call(
                with_output_limit(model, 4500),
                SuggestedRevision,
                [SystemMessage(render_prompt("verifier_update")), HumanMessage(data)],
                agent=AGENT,
                step="préparer la correction",
                intent="drafting an update for the API change",
                retries=1,
            )
            await port.prepare(deps.user_id, deps.session_id, proposal, result)
        return {"summary": "A lesson update is ready to review."}

    graph = StateGraph(UpdateState)
    graph.add_node("review", review)
    graph.add_edge(START, "review")
    graph.add_edge("review", END)
    return graph
