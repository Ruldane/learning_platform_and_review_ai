"""Deux plaidoiries d’architecture sur la même copie, puis publication atomique."""

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.code_trial_port import (
    DEFENDER,
    PROSECUTOR,
    CodeArgument,
    CodePassage,
    CodePleading,
)
from app.core.errors import AppError
from app.providers.llm.limits import with_output_limit


class TrialInput(BaseModel):
    trial_id: str = Field(min_length=36, max_length=36)


class TrialState(TypedDict, total=False):
    trial_id: str
    prosecution: dict[str, Any]
    defense: dict[str, Any]
    summary: str


def _citations(result: CodeArgument, passages: list[CodePassage]) -> list[CodePassage]:
    selected = [
        passages[i - 1] for i in dict.fromkeys(result.references) if 1 <= i <= len(passages)
    ]
    if not selected:
        raise AppError(
            "code_trial_citation_missing",
            "Une plaidoirie doit citer un passage de cette version.",
            502,
        )
    return selected


async def _argue(deps: GraphDeps, state: TrialState, role: str) -> CodeArgument:
    available = await deps.ports.code_trial.passages(
        deps.user_id, deps.session_id, state["trial_id"]
    )
    catalog = [{"reference": index, **item.model_dump()} for index, item in enumerate(available, 1)]
    other = (
        CodeArgument.model_validate(state["prosecution"]).argument if "prosecution" in state else ""
    )
    request = untrusted(json.dumps(catalog, ensure_ascii=False), "extraits du projet figé")
    if other:
        request += "\n\n" + untrusted(other, "plaidoirie du Procureur")
    model = await deps.models.get_chat_model(deps.user_id, get_agent(role).tier, agent=role)
    reply = await structured_call(
        with_output_limit(model, 1250),
        CodeArgument,
        [SystemMessage(render_prompt(role)), HumanMessage(request)],
        agent=role,
        step="plaidoirie",
        intent="j’examine la conception du projet figé",
        retries=1,
    )
    _citations(reply, available)
    return reply


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def prosecute(state: TrialState) -> TrialState:
        reply = await _argue(deps, state, PROSECUTOR)
        return {"prosecution": reply.model_dump()}

    async def defend(state: TrialState) -> TrialState:
        reply = await _argue(deps, state, DEFENDER)
        return {"defense": reply.model_dump()}

    async def publish(state: TrialState) -> TrialState:
        trial_id = state["trial_id"]
        available = await deps.ports.code_trial.passages(deps.user_id, deps.session_id, trial_id)
        first = CodeArgument.model_validate(state["prosecution"])
        second = CodeArgument.model_validate(state["defense"])
        await deps.ports.code_trial.save(
            deps.user_id,
            deps.session_id,
            trial_id,
            [
                CodePleading(
                    role="prosecutor",
                    argument=first.argument,
                    citations=_citations(first, available),
                ),
                CodePleading(
                    role="defender",
                    argument=second.argument,
                    citations=_citations(second, available),
                ),
            ],
        )
        return {"summary": "Les deux plaidoiries sont disponibles."}

    graph = StateGraph(TrialState)
    graph.add_node("prosecute", prosecute)
    graph.add_node("defend", defend)
    graph.add_node("publish", publish)
    graph.add_edge(START, "prosecute")
    graph.add_edge("prosecute", "defend")
    graph.add_edge("defend", "publish")
    graph.add_edge("publish", END)
    return graph
