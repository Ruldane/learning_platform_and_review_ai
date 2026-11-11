"""Outils mémoire des agents (SPEC 4.4, 4.5, D68) : des fonctions appelables depuis un nœud, qui
annoncent leur appel (`tool.called`), rendent leur issue (`tool.result`) et, pour une écriture,
publient `memory.written` ; plus `memory_tools_for`, les mêmes outils sous forme de
`StructuredTool` pour l'appel d'outils par le LLM (phases suivantes).

La mémoire elle-même est derrière le port `MemoryGateway` (`GraphDeps.memory`). Les événements
portent des titres et des raisons ; les journaux, eux, ne citent jamais de contenu."""

from collections.abc import Sequence
from typing import Any, Literal
from uuid import uuid4

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

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
    """Recherche sémantique dans la mémoire de l'utilisatrice (8 résultats par défaut)."""
    shown = None if kinds is None else list(kinds)
    call_id = _call(agent, "memory_search", {"query": query, "kinds": shown, "k": k})
    try:
        found = await deps.memory.search(deps.user_id, query, kinds=kinds, k=k)
    except AppError as exc:
        _failed(agent, call_id, "memory_search", exc)
        raise
    _result(agent, call_id, "memory_search", ok=True, summary=f"{len(found.hits)} fragment(s)")
    return found


async def memory_write(deps: GraphDeps, write: AgentWrite, *, agent: str) -> WriteResult:
    """Écrit dans la mémoire, journalisé avec l'agent, la session et la raison. Un contenu déjà
    présent n'écrit rien (`created` faux, pas de `memory.written`) : un nœud rejoué ne double
    jamais une écriture."""
    args = {"kind": write.kind, "title": write.title, "tags": list(write.tags)}
    call_id = _call(agent, "memory_write", args)
    try:
        done = await deps.memory.write(deps.user_id, deps.session_id, agent, write)
    except AppError as exc:
        _failed(agent, call_id, "memory_write", exc)
        raise
    summary = f"Écrit : {done.title}" if done.created else f"Déjà en mémoire : {done.title}"
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
    """Acquis connus de l'utilisatrice, par niveau (lus dans la mémoire jusqu'à la phase 4)."""
    call_id = _call(agent, "memory_get_skills", {})
    try:
        skills = await deps.memory.skills(deps.user_id)
    except AppError as exc:
        _failed(agent, call_id, "memory_get_skills", exc)
        raise
    _result(agent, call_id, "memory_get_skills", ok=True, summary=f"{skills.total} acquis")
    return skills


# --- Outils pour l'appel d'outils par le LLM --------------------------------------------------


class _SearchArgs(BaseModel):
    query: str = Field(description="Ce qu'on cherche, en une phrase.")
    kinds: list[str] | None = Field(
        default=None,
        description="Types à chercher : document, acquis, lecon, source, offre, decision.",
    )
    k: int = Field(default=DEFAULT_K, ge=1, le=50, description="Nombre de fragments.")


class _WriteArgs(BaseModel):
    kind: AgentWritableKind
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    reason: str = Field(min_length=1, description="La raison de l'écriture, en une phrase.")
    tags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    level: Literal["declare", "en_cours"] | None = None
    source_id: str | None = None


class _NoArgs(BaseModel):
    pass


def memory_tools_for(deps: GraphDeps, *, agent: str) -> list[BaseTool]:
    """`memory_search`, `memory_write` et `memory_get_skills`, liés à `deps` et à `agent`. Chaque
    outil rend du texte au modèle (le texte d'un fragment y est encadré comme non fiable)."""

    async def search(query: str, kinds: list[str] | None = None, k: int = DEFAULT_K) -> str:
        return (await memory_search(deps, query, kinds, k, agent=agent)).agent_text

    async def write(**fields: Any) -> str:
        done = await memory_write(deps, _to_write(_WriteArgs(**fields)), agent=agent)
        if not done.created:
            return f"Déjà en mémoire : {done.title}"
        pending = " (à confirmer par January)" if done.status == "pending" else ""
        return f"Écrit : {done.title}{pending}"

    async def skills() -> str:
        return (await memory_get_skills(deps, agent=agent)).as_agent_text()

    return [
        StructuredTool.from_function(
            coroutine=search,
            name="memory_search",
            description="Cherche dans la mémoire de January (documents, acquis, leçons…).",
            args_schema=_SearchArgs,
        ),
        StructuredTool.from_function(
            coroutine=write,
            name="memory_write",
            description="Écrit un élément en mémoire, avec la raison de l'écriture.",
            args_schema=_WriteArgs,
        ),
        StructuredTool.from_function(
            coroutine=skills,
            name="memory_get_skills",
            description="Liste les acquis de January, avec leur niveau.",
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
