"""Collect bounded diagnostics and ask the reviewer to score the submission."""

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.boss_port import BOSS_AGENT, BossRubric


class BossReviewInput(BaseModel):
    program_id: str = Field(min_length=36, max_length=36)


class BossReviewState(TypedDict, total=False):
    program_id: str
    summary: str
    total: int


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def review(state: BossReviewState) -> BossReviewState:
        port = deps.ports.boss
        program_id = state["program_id"]
        submission = await port.diagnose(deps.user_id, program_id, deps.session_id)
        grade = submission.previous
        if grade is None:
            facts = submission.model_dump(exclude={"code_sample", "previous"})
            prompt = render_prompt(
                BOSS_AGENT,
                facts=json.dumps(facts, ensure_ascii=False),
                code=untrusted(
                    json.dumps(submission.code_sample, ensure_ascii=False), "code remis"
                ),
            )
            model = await deps.models.get_chat_model(
                deps.user_id, get_agent(BOSS_AGENT).tier, agent=BOSS_AGENT
            )
            rubric = await structured_call(
                model,
                BossRubric,
                [SystemMessage(prompt), HumanMessage("Assess the submission on both criteria.")],
                agent=BOSS_AGENT,
                step="boss",
                intent="assessing readability and maintainability",
                retries=0,
            )
            grade = await port.grade(deps.user_id, program_id, deps.session_id, rubric)
        return {"summary": "The boss challenge has been graded.", "total": grade.total}

    graph = StateGraph(BossReviewState)
    graph.add_node("review", review)
    graph.add_edge(START, "review")
    graph.add_edge("review", END)
    return graph
