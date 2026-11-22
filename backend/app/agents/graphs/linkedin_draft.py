"""Le Recruteur réordonne et reformule les éléments déjà vérifiés."""

import json
from dataclasses import asdict
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.linkedin_profile import LinkedInText

AGENT = "recruiter"


class LinkedInInput(BaseModel):
    draft_id: str = Field(min_length=36, max_length=36)


class LinkedInState(TypedDict):
    draft_id: str


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def write(state: LinkedInState) -> dict[str, str]:
        draft_id = state["draft_id"]
        store = deps.ports.linkedin
        context = await store.context(deps.user_id, deps.session_id, draft_id)
        if context.finished:
            return {}
        agent = get_agent(AGENT)
        model = await deps.models.get_chat_model(deps.user_id, agent.tier, agent=AGENT)
        text = await structured_call(
            model,
            LinkedInText,
            [
                SystemMessage(render_prompt("linkedin_draft")),
                HumanMessage(
                    untrusted(json.dumps(asdict(context), ensure_ascii=False), "profil et cible")
                ),
            ],
            agent=AGENT,
            step="linkedin_draft",
            intent="je formule le profil à partir des faits confirmés",
            retries=1,
        )
        await store.propose(deps.user_id, deps.session_id, draft_id, text)
        return {}

    graph = StateGraph(LinkedInState)
    graph.add_node("write", write)
    graph.add_edge(START, "write")
    graph.add_edge("write", END)
    return graph
