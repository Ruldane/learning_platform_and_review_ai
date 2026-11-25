"""Memory port for the agents (D68). `app.agents` imports no feature (contract 6): it
describes here what it needs; the composition (`app.bootstrap.memory_gateway`) plugs in
the `memory` feature implementation, as for `RunSettingsSource`.

Every text returned to an agent (`agent_text`) frames imported content with `untrusted()` (17.4).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.prompts.loader import untrusted
from app.core.errors import AppError

# Types an agent may write: never a `document` (reserved for import).
AgentWritableKind = Literal["skill", "lesson", "source", "posting", "decision"]
NO_SKILLS = "No skills in memory."


@dataclass(frozen=True)
class MemoryHitView:
    item_id: str
    chunk_id: str
    kind: str
    title: str
    text: str
    score: float
    created_by: str


@dataclass(frozen=True)
class MemorySearchResult:
    hits: list[MemoryHitView]
    agent_text: str


@dataclass(frozen=True)
class AgentWrite:
    kind: AgentWritableKind
    title: str
    text: str
    reason: str
    tags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    level: Literal["declared", "in_progress"] | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class WriteResult:
    item_id: str
    kind: str
    title: str
    status: Literal["active", "pending"]
    created: bool  # false: the same content was already in memory (nothing written)


@dataclass(frozen=True)
class SkillEntry:
    item_id: str
    title: str
    level: str
    tags: list[str]


def _one_line(text: str) -> str:
    return " ".join(text.split())


@dataclass(frozen=True)
class SkillsSummary:
    total: int
    by_level: dict[str, int]
    skills: list[SkillEntry]

    def as_text(self) -> str:
        """List the skills with each title condensed to one line."""
        if not self.skills:
            return NO_SKILLS
        lines = [f"Skills ({self.total})"]
        lines += [f"- {_one_line(skill.title)} — {skill.level}" for skill in self.skills]
        return "\n".join(lines)

    def as_agent_text(self) -> str:
        """`as_text` framed as untrusted content (17.4): a skill title may come from an
        imported document (Archivist). To pass as is to an agent (prompt, tool return)."""
        return untrusted(self.as_text(), "memory:skills")


@dataclass(frozen=True)
class DocumentText:
    document_id: str
    title: str
    chunks: list[str] = field(default_factory=list)


class MemoryGateway(Protocol):
    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None, k: int
    ) -> MemorySearchResult: ...

    async def write(
        self, user_id: str, session_id: str, author: str, write: AgentWrite
    ) -> WriteResult: ...

    async def skills(self, user_id: str) -> SkillsSummary: ...

    async def document_text(
        self, user_id: str, document_id: str, *, max_chunks: int
    ) -> DocumentText | None: ...


def memory_unavailable() -> AppError:
    return AppError("memory_unavailable", "Memory is unavailable in this runtime.", 503)


class _NoMemory:
    """Engine default value (existing tests, starts without memory)."""

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None, k: int
    ) -> MemorySearchResult:
        raise memory_unavailable()

    async def write(
        self, user_id: str, session_id: str, author: str, write: AgentWrite
    ) -> WriteResult:
        raise memory_unavailable()

    async def skills(self, user_id: str) -> SkillsSummary:
        raise memory_unavailable()

    async def document_text(
        self, user_id: str, document_id: str, *, max_chunks: int
    ) -> DocumentText | None:
        raise memory_unavailable()


NO_MEMORY: MemoryGateway = _NoMemory()
