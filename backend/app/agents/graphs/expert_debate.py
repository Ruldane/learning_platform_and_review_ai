"""Read the source catalog and resume the debate between each of its three speakers."""

import re
from typing import Any, Protocol, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.nodes.committee.common import DEBATE_REQUEST, role_call
from app.agents.nodes.expert_sources import ExpertSource, debate_sources
from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import message_text, node_timeout
from app.agents.runtime.speech import CitationEntry, speak
from app.agents.tools.committee_schema import MAX_WORDS
from app.agents.tools.conversation_port import TURN_TOKEN_LIMIT
from app.agents.tools.expert_debate_port import (
    ExpertCitation,
    ExpertRole,
    ExpertSpeech,
)
from app.core.errors import AppError
from app.providers.llm.limits import with_output_limit

_ACTORS: dict[ExpertRole, str] = {
    "researcher": "scout",
    "practitioner": "practitioner",
    "skeptic": "skeptic",
}
_LABELS: dict[ExpertRole, str] = {
    "researcher": "Chercheur",
    "practitioner": "Praticien",
    "skeptic": "Sceptique",
}
_MARKERS = re.compile(r"\[(\d{1,4}(?:\s*,\s*\d{1,4})*)\]")


class ExpertDebateInput(BaseModel):
    thread_id: UUID
    turn_id: UUID


class ExpertState(TypedDict, total=False):
    thread_id: str
    turn_id: str
    sources: list[dict[str, Any]]
    speeches: list[dict[str, Any]]
    saved: bool
    summary: str


class ExpertNode(Protocol):
    async def __call__(self, state: ExpertState) -> ExpertState: ...


def _arguments(deps: GraphDeps, state: ExpertState) -> tuple[str, str, str, str]:
    return (deps.user_id, deps.session_id, state["thread_id"], state["turn_id"])


def _safe_markers(text: str, indices: set[int]) -> str:
    def replacement(match: re.Match[str]) -> str:
        kept = [str(int(part)) for part in match[1].split(",") if int(part) in indices]
        return f"[{', '.join(kept)}]" if kept else ""

    return _MARKERS.sub(replacement, text).strip()


def _prompt(
    role: ExpertRole,
    question: str,
    sources: list[ExpertSource],
    speeches: list[ExpertSpeech],
) -> dict[str, object]:
    return {
        "role": _LABELS[role],
        "question": untrusted(question[:1_500], "user's question"),
        "catalog": "\n\n".join(
            f"[{source.index}] {untrusted(source.title + '\n' + source.material, 'web page read')}"
            for source in sources
        ),
        "previous": untrusted(
            "\n".join(f"{_LABELS[entry.role]} — {entry.text[:320]}" for entry in speeches),
            "previous statements",
        ),
    }


def make_speech(deps: GraphDeps, role: ExpertRole) -> ExpertNode:
    @node_timeout(90)
    async def reply(state: ExpertState) -> ExpertState:
        draft = await deps.ports.expert_debates.draft(*_arguments(deps, state))
        if draft.saved:
            return {"saved": True}
        sources = [ExpertSource.model_validate(item) for item in state.get("sources", [])]
        speeches = [ExpertSpeech.model_validate(entry) for entry in state.get("speeches", [])]
        agent = _ACTORS[role]
        model, messages = await role_call(
            deps,
            agent,
            "expert_debate",
            DEBATE_REQUEST,
            _prompt(role, draft.question, sources, speeches),
            tier="strong" if draft.strong else None,
        )
        cap = min(TURN_TOKEN_LIMIT, deps.settings.session_token_cap)
        estimated = sum(len(message_text(message).encode()) for message in messages)
        output = min(600, cap - draft.used_tokens - estimated)
        if output < 200:
            raise AppError(
                "conversation_budget_reached", "The debate budget has been reached.", 429
            )
        said = await speak(
            with_output_limit(model, output),
            messages,
            agent=agent,
            step=f"debate_{role}",
            intent="answering the question in light of the other experts' statements",
            catalog=[
                CitationEntry(source.index, source.title, str(source.url)) for source in sources
            ],
            max_words=MAX_WORDS,
            retry=False,
        )
        valid = {citation.index for citation in said.citations}
        text = _safe_markers(said.text, valid)
        if not text:
            raise AppError("debate_speech_empty", "One of the experts did not respond.", 503)
        by_index = {source.index: source for source in sources}
        citations = [
            ExpertCitation(index=index, title=by_index[index].title, url=by_index[index].url)
            for index in (citation.index for citation in said.citations)
        ]
        speeches.append(ExpertSpeech(role=role, text=text, citations=citations))
        return {"speeches": [speech.model_dump(mode="json") for speech in speeches]}

    return reply


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    @node_timeout(90)
    async def research(state: ExpertState) -> ExpertState:
        draft = await deps.ports.expert_debates.draft(*_arguments(deps, state))
        if draft.saved:
            return {"saved": True, "summary": "Debate complete."}
        sources = await debate_sources(deps, draft.question)
        return {"sources": [source.model_dump(mode="json") for source in sources]}

    async def save(state: ExpertState) -> ExpertState:
        if not state.get("saved"):
            speeches = [ExpertSpeech.model_validate(entry) for entry in state["speeches"]]
            await deps.ports.expert_debates.publish(*_arguments(deps, state), speeches)
        return {"summary": "Debate complete."}

    graph = StateGraph(ExpertState)
    graph.add_node("research", research)
    graph.add_node("save", save)
    graph.add_edge(START, "research")
    graph.add_node("researcher", make_speech(deps, "researcher"))
    graph.add_node("practitioner", make_speech(deps, "practitioner"))
    graph.add_node("skeptic", make_speech(deps, "skeptic"))
    graph.add_conditional_edges(
        "research",
        lambda state: "done" if state.get("saved") else "speak",
        {"done": END, "speak": "researcher"},
    )
    graph.add_edge("researcher", "practitioner")
    graph.add_edge("practitioner", "skeptic")
    graph.add_edge("skeptic", "save")
    graph.add_edge("save", END)
    return graph
