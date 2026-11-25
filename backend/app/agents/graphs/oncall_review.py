"""Assess the incident report and save the assessment idempotently."""

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.oncall_port import ReviewScore

AGENT = "oncall_reviewer"


class OncallReviewInput(BaseModel):
    incident_id: str = Field(min_length=36, max_length=36)


class OncallReviewState(TypedDict, total=False):
    incident_id: str
    summary: str
    score: int
    proof_recorded: bool


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def review(state: OncallReviewState) -> OncallReviewState:
        port = deps.ports.oncall
        incident_id = state["incident_id"]
        snapshot = await port.read(deps.user_id, incident_id, deps.session_id)
        score = snapshot.previous
        if score is None:
            context = json.dumps(snapshot.model_dump(exclude={"previous"}), ensure_ascii=False)
            prompt = render_prompt(AGENT, context=untrusted(context, "dossier d’astreinte"))
            model = await deps.models.get_chat_model(
                deps.user_id, get_agent(AGENT).tier, agent=AGENT
            )
            score = await structured_call(
                model,
                ReviewScore,
                [SystemMessage(prompt), HumanMessage("Assess the report.")],
                agent=AGENT,
                step="rapport",
                intent="assessing the reasoning in the report",
            )
        proved = await port.record(deps.user_id, incident_id, deps.session_id, score)
        return {
            "summary": "On-call report graded.",
            "score": score.total,
            "proof_recorded": proved,
        }

    graph = StateGraph(OncallReviewState)
    graph.add_node("review", review)
    graph.add_edge(START, "review")
    graph.add_edge("review", END)
    return graph
