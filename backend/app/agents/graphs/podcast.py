"""Publish the episode script before requesting its audio."""

import json
from typing import Any, Self, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.tools.podcast_port import PodcastContext, PodcastScript

AGENT = "podcast_host"


class PodcastInput(BaseModel):
    episode_id: str = Field(min_length=36, max_length=36)


class PodcastDraft(PodcastScript):
    @model_validator(mode="after")
    def check_length(self) -> Self:
        words = sum(len(line.text.split()) for line in self.lines)
        if not 1_550 <= words <= 1_850:
            raise ValueError("The dialogue must contain between 1,550 and 1,850 words.")
        return self


class PodcastState(TypedDict, total=False):
    episode_id: str
    summary: str


def _messages(context: PodcastContext) -> list[BaseMessage]:
    source = json.dumps(
        {
            "chapter": context.lesson_title,
            "text": context.lesson_text,
            "review_material": context.reviews,
            "notes": context.notes,
        },
        ensure_ascii=False,
    )
    return [
        SystemMessage(render_prompt(AGENT)),
        HumanMessage(untrusted(source, "episode sources")),
    ]


async def _draft(deps: GraphDeps, episode_id: str) -> None:
    store = deps.ports.podcast
    context = await store.context(deps.user_id, episode_id)
    if context.already_written:
        return
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    script = await structured_call(
        model,
        PodcastDraft,
        _messages(context),
        agent=AGENT,
        step="dialogue",
        intent="writing the dialogue and three questions",
        retries=1,
    )
    await store.save_script(deps.user_id, episode_id, script)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def write(state: PodcastState) -> PodcastState:
        await _draft(deps, state["episode_id"])
        return {}

    async def voice(state: PodcastState) -> PodcastState:
        await deps.ports.podcast.render_audio(deps.user_id, state["episode_id"])
        return {"summary": "The morning podcast is ready."}

    graph = StateGraph(PodcastState)
    graph.add_node("write", write)
    graph.add_node("voice", voice)
    graph.add_edge(START, "write")
    graph.add_edge("write", "voice")
    graph.add_edge("voice", END)
    return graph
