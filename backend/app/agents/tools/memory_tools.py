"""Memory tools for the agents (SPEC 4.4, 4.5, D68): callable functions from a node, which
announce their call (`tool.called`), return their outcome (`tool.result`) and, for a write,
publish `memory.written`; plus `memory_tools_for`, the same tools as
`StructuredTool` for the LLM's tool calls (later phases).

The memory itself sits behind the `MemoryGateway` port (`GraphDeps.memory`). Events
carry titles and reasons; the logs, for their part, never quote content."""

from collections.abc import Sequence
from typing import Any, Literal
from uuid import uuid4

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, field_validator

from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.tools.memory_port import (
    AgentWritableKind,
    AgentWrite,
    MemorySearchResult,
    SkillsSummary,
    WriteResult,
)
from app.core.errors import AppError
from app.db.models.memory import current_memory_kind

DEFAULT_K = 8


def _call(agent: str, tool: str, args: dict[str, Any]) -> str:
    call_id = uuid4().hex
    emit("tool.called", {"call_id": call_id, "tool": tool, "args": args}, agent=agent)
    return call_id


def _result(agent: str, call_id: str, tool: str, *, ok: bool, summary: str) -> None:
    emit(
        "tool.result",
        {"call_id": call_id, "tool": tool, "ok": ok, "summary": summary},
        agent=agent,
    )


def _failed(agent: str, call_id: str, tool: str, exc: AppError) -> None:
    _result(agent, call_id, tool, ok=False, summary=exc.message)


async def memory_search(
    deps: GraphDeps,
    query: str,
    kinds: Sequence[str] | None = None,
    k: int = DEFAULT_K,
    *,
    agent: str,
) -> MemorySearchResult:
    """Semantic search in the user's memory (8 results by default)."""
    shown = None if kinds is None else list(kinds)
    call_id = _call(agent, "memory_search", {"query": query, "kinds": shown, "k": k})
    try:
        found = await deps.memory.search(deps.user_id, query, kinds=kinds, k=k)
    except AppError as exc:
        _failed(agent, call_id, "memory_search", exc)
        raise
    _result(agent, call_id, "memory_search", ok=True, summary=f"{len(found.hits)} result(s)")
    return found


async def memory_write(deps: GraphDeps, write: AgentWrite, *, agent: str) -> WriteResult:
    """Writes to memory, logged with the agent, the session and the reason. Content already
    present writes nothing (`created` false, no `memory.written`): a replayed node never doubles
    a write."""
    args = {"kind": write.kind, "title": write.title, "tags": list(write.tags)}
    call_id = _call(agent, "memory_write", args)
    try:
        done = await deps.memory.write(deps.user_id, deps.session_id, agent, write)
    except AppError as exc:
        _failed(agent, call_id, "memory_write", exc)
        raise
    summary = f"Saved “{done.title}”." if done.created else f"“{done.title}” is already in memory."
    _result(agent, call_id, "memory_write", ok=True, summary=summary)
    if done.created:
        emit(
            "memory.written",
            {
                "item_id": done.item_id,
                "kind": done.kind,
                "title": done.title,
                "reason": write.reason,
                "status": done.status,
            },
            agent=agent,
        )
    return done


async def memory_get_skills(deps: GraphDeps, *, agent: str) -> SkillsSummary:
    """Skills known to the user, by level (read from memory up to phase 4)."""
    call_id = _call(agent, "memory_get_skills", {})
    try:
        skills = await deps.memory.skills(deps.user_id)
    except AppError as exc:
        _failed(agent, call_id, "memory_get_skills", exc)
        raise
    _result(agent, call_id, "memory_get_skills", ok=True, summary=f"{skills.total} skill(s)")
    return skills


# --- Tools for the LLM's tool calls ---


class _SearchArgs(BaseModel):
    query: str = Field(description="What to search for, in one sentence.")
    kinds: list[str] | None = Field(
        default=None,
        description="Kinds to search: document, skill, lesson, source, posting, decision.",
    )
    k: int = Field(default=DEFAULT_K, ge=1, le=50, description="Number of chunks to return.")


class _WriteArgs(BaseModel):
    kind: AgentWritableKind
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    reason: str = Field(min_length=1, description="Why the item should be saved, in one sentence.")
    tags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    level: Literal["declared", "in_progress"] | None = None
    source_id: str | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def read_checkpoint_kind(cls, value: object) -> object:
        return current_memory_kind(value) if isinstance(value, str) else value


class _NoArgs(BaseModel):
    pass


def memory_tools_for(deps: GraphDeps, *, agent: str) -> list[BaseTool]:
    """`memory_search`, `memory_write` and `memory_get_skills`, bound to `deps` and to `agent`. Each
    tool returns text to the model (a fragment's text and an item's title already in memory
    are framed there as untrusted)."""

    async def search(query: str, kinds: list[str] | None = None, k: int = DEFAULT_K) -> str:
        return (await memory_search(deps, query, kinds, k, agent=agent)).agent_text

    async def write(**fields: Any) -> str:
        done = await memory_write(deps, _to_write(_WriteArgs(**fields)), agent=agent)
        if not done.created:  # title read from memory (an imported document may have set it)
            return f"Already in memory\n{untrusted(done.title, 'title in memory')}"
        pending = " (awaiting January’s confirmation)" if done.status == "pending" else ""
        return f"Saved “{done.title}”{pending}."

    async def skills() -> str:
        return (await memory_get_skills(deps, agent=agent)).as_agent_text()

    return [
        StructuredTool.from_function(
            coroutine=search,
            name="memory_search",
            description="Search January's memory, including documents, skills, and lessons.",
            args_schema=_SearchArgs,
        ),
        StructuredTool.from_function(
            coroutine=write,
            name="memory_write",
            description="Save an item to memory with the reason it should be kept.",
            args_schema=_WriteArgs,
        ),
        StructuredTool.from_function(
            coroutine=skills,
            name="memory_get_skills",
            description="List January's skills and their current levels.",
            args_schema=_NoArgs,
        ),
    ]


def _to_write(args: _WriteArgs) -> AgentWrite:
    return AgentWrite(
        kind=args.kind,
        title=args.title,
        text=args.text,
        reason=args.reason,
        tags=tuple(args.tags),
        evidence=tuple(args.evidence),
        level=args.level,
        source_id=args.source_id,
    )
