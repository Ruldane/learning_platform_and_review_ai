"""Le Vérificateur prépare et évalue une copie du chapitre."""

import json
from typing import Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.lesson_hunt_port import ErrorPair, HuntAssessment, HuntContext
from app.core.errors import AppError

AGENT = "verifier"


class LessonHuntInput(BaseModel):
    hunt_id: str = Field(min_length=36, max_length=36)


class HuntGraphState(TypedDict, total=False):
    hunt_id: str
    summary: str


def _messages(data: dict[str, Any], task: str) -> list[BaseMessage]:
    return [
        SystemMessage(render_prompt("lesson_hunt", task=task)),
        HumanMessage(untrusted(json.dumps(data, ensure_ascii=False), "données de l’exercice")),
    ]


async def _prepare(deps: GraphDeps, hunt_id: str, context: HuntContext) -> str:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    changes = await structured_call(
        model,
        ErrorPair,
        _messages({"titre": context.title, "chapitre": context.source[:35_000]}, "préparation"),
        agent=AGENT,
        step="preparer_lecture",
        intent="je prépare deux passages à examiner",
        retries=1,
    )
    await deps.ports.lesson_hunt.publish(deps.user_id, hunt_id, deps.session_id, changes)
    return "Deux erreurs sont à repérer."


async def _assess(deps: GraphDeps, hunt_id: str, context: HuntContext) -> str:
    if context.errors is None or context.responses is None:
        raise AppError("lesson_hunt_incomplete", "The exercise answers are missing.", 409)
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    feedback = await structured_call(
        model,
        HuntAssessment,
        _messages(
            {"corrections": context.errors.model_dump(), "réponses": context.responses}, "bilan"
        ),
        agent=AGENT,
        step="corriger_lecture",
        intent="je compare les deux explications à la correction",
        retries=1,
    )
    await deps.ports.lesson_hunt.assess(deps.user_id, hunt_id, deps.session_id, feedback)
    return "La correction est disponible."


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def work(state: HuntGraphState) -> HuntGraphState:
        hunt_id = state["hunt_id"]
        context = await deps.ports.lesson_hunt.context(deps.user_id, hunt_id, deps.session_id)
        if context.stage == "preparing":
            summary = await _prepare(deps, hunt_id, context)
        elif context.stage == "reviewing":
            summary = await _assess(deps, hunt_id, context)
        else:
            summary = "The reading exercise is already available."
        return {"summary": summary}

    graph = StateGraph(HuntGraphState)
    graph.add_node("work", work)
    graph.add_edge(START, "work")
    graph.add_edge("work", END)
    return graph
