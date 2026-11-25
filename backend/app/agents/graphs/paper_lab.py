"""Read the paper and prepare a short lesson on its method and experiment."""

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.paper_lab_port import ArticleSource, PaperDraft
from app.core.errors import AppError

AGENT = "writer"


class PaperLabInput(BaseModel):
    lab_id: str = Field(min_length=36, max_length=36)


class PaperLabState(TypedDict, total=False):
    lab_id: str
    summary: str


async def _read(deps: GraphDeps, url: str) -> ArticleSource:
    page = await deps.ports.web.read(deps.user_id, deps.session_id, url)
    if page.status != "ok" or len(page.text.strip()) < 100:
        raise AppError("paper_lab_source", "The text of this paper is unavailable.", 422)
    return ArticleSource(page.url, page.title or "Article source", page.text[:28_000])


async def _prepare(deps: GraphDeps, source: ArticleSource) -> PaperDraft:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        PaperDraft,
        [
            SystemMessage(render_prompt("paper_lab")),
            HumanMessage(
                untrusted(
                    json.dumps(
                        {"title": source.title, "text": source.material}, ensure_ascii=False
                    ),
                    "main text of the paper",
                )
            ),
        ],
        agent=AGENT,
        step="experience_article",
        intent="connecting the paper's method to an experiment",
        retries=1,
    )


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def prepare(state: PaperLabState) -> PaperLabState:
        lab_id = state["lab_id"]
        store = deps.ports.paper_lab
        context = await store.context(deps.user_id, lab_id, deps.session_id)
        if not context.published:
            source = await _read(deps, context.url)
            draft = await _prepare(deps, source)
            await store.publish(deps.user_id, lab_id, deps.session_id, source, draft)
        return {"summary": "The short lesson and notebook are ready."}

    graph = StateGraph(PaperLabState)
    graph.add_node("prepare", prepare)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", END)
    return graph
