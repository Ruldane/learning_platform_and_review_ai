"""Nodes of the Archivist (flow `learned_document`): read the document, extract its concepts,
write them as declared acquired skills. Each node is a function of `GraphDeps`."""

from typing import Any, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.prose import Prose
from app.agents.runtime.structured import structured_call
from app.agents.state.learned_document import LearnedDocumentState
from app.agents.tools.memory_port import AgentWrite
from app.agents.tools.memory_tools import memory_get_skills, memory_write
from app.core.errors import AppError

AGENT = "archivist"
MAX_CHUNKS = 24  # ~12,000 tokens of document
MAX_CONCEPTS = 20  # requested from the model; the schema tolerates up to 30
WRITE_TIMEOUT_S = 300  # one vectorization per concept


class Node(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: LearnedDocumentState) -> LearnedDocumentState: ...


class Concept(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    summary: Prose = Field(min_length=1, max_length=400)
    tags: list[str] = Field(default_factory=list, max_length=5)


class ExtractedConcepts(BaseModel):
    concepts: list[Concept] = Field(max_length=30)


def _not_found() -> AppError:
    return AppError("document_not_found", "Document not found.", 404)


def make_load_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load_context(state: LearnedDocumentState) -> LearnedDocumentState:
        emit(
            "agent.started",
            {"step": "lecture", "intent": "I am reading the document and your known skills"},
            agent=AGENT,
        )
        document = await deps.memory.document_text(
            deps.user_id, state["document_id"], max_chunks=MAX_CHUNKS
        )
        if document is None:
            raise _not_found()
        skills = await memory_get_skills(deps, agent=AGENT)
        return {
            "title": " ".join(document.title.split()),
            "text": "\n\n".join(document.chunks),
            "known": skills.as_text(),
        }

    return load_context


def make_extract(deps: GraphDeps) -> Node:
    @node_timeout()
    async def extract(state: LearnedDocumentState) -> LearnedDocumentState:
        prompt = render_prompt(
            AGENT,
            mode="learned",
            title=untrusted(state["title"], "title"),
            known=untrusted(state["known"], "memory:learned"),
            document=untrusted(state["text"], "document"),
            max_concepts=MAX_CONCEPTS,
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        found = await structured_call(
            model,
            ExtractedConcepts,
            [SystemMessage(prompt), HumanMessage("Extract the concepts from the document.")],
            agent=AGENT,
            step="extraction",
            intent="extracting concepts from the document",
        )
        concepts = [c for c in found.concepts if c.title.strip() and c.summary.strip()]
        return {"concepts": [c.model_dump() for c in concepts[:MAX_CONCEPTS]]}

    return extract


def _write_of(state: LearnedDocumentState, concept: dict[str, Any]) -> AgentWrite:
    """Skill at the `declare` level (SPEC 4.3), linked to the document. The same write replayed
    is recognized by its title (D64 4): never a second skill."""
    document_id = state["document_id"]
    return AgentWrite(
        kind="skill",
        title=concept["title"],
        text=concept["summary"],
        tags=tuple(concept["tags"]),
        evidence=(document_id,),
        level="declared",
        source_id=document_id,
        reason=f'Document "{state["title"]}" marked "already learned".',
    )


def make_write(deps: GraphDeps) -> Node:
    @node_timeout(WRITE_TIMEOUT_S)
    async def write(state: LearnedDocumentState) -> LearnedDocumentState:
        created = known = 0
        for concept in state.get("concepts", []):
            done = await memory_write(deps, _write_of(state, concept), agent=AGENT)
            created, known = created + done.created, known + (not done.created)
        return {"created": created, "already_known": known}

    return write


async def finalize(state: LearnedDocumentState) -> LearnedDocumentState:
    added = state.get("created", 0)
    skills = "skill" if added == 1 else "skills"
    return {
        "summary": (
            f"Added {added} {skills} to memory. {state.get('already_known', 0)} already known."
        )
    }
