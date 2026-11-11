from collections.abc import Sequence
from dataclasses import dataclass, field

import pytest

from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.run_settings import RunSettings
from app.agents.tools.memory_port import (
    AgentWrite,
    DocumentText,
    MemoryHitView,
    MemorySearchResult,
    SkillEntry,
    SkillsSummary,
    WriteResult,
)
from tests.agents.runtime.conftest import emitted  # noqa: F401  (fixture partagée)


@dataclass
class FakeGateway:
    """Mémoire factice : enregistre les appels, rend des valeurs fixes."""

    searches: list[tuple[str, tuple[str, ...] | None, int]] = field(default_factory=list)
    writes: list[tuple[str, str, str, AgentWrite]] = field(default_factory=list)
    created: bool = True
    skill_title: str = "Python"
    existing_title: str | None = None  # titre en mémoire d'un contenu déjà présent

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None, k: int
    ) -> MemorySearchResult:
        self.searches.append((query, None if kinds is None else tuple(kinds), k))
        hits = [
            MemoryHitView(f"i{n}", f"c{n}", "acquis", "Attention", "t", 0.8, "user") for n in "123"
        ]
        return MemorySearchResult(hits, "Mémoire — 3 fragment(s)")

    async def write(
        self, user_id: str, session_id: str, author: str, write: AgentWrite
    ) -> WriteResult:
        self.writes.append((user_id, session_id, author, write))
        status = "pending" if write.kind == "decision" else "active"
        title = write.title if self.created else (self.existing_title or write.title)
        return WriteResult("item-1", write.kind, title, status, self.created)

    async def skills(self, user_id: str) -> SkillsSummary:
        skill = SkillEntry("a1", self.skill_title, "declare", [])
        return SkillsSummary(1, {"declare": 1}, [skill])

    async def document_text(
        self, user_id: str, document_id: str, *, max_chunks: int
    ) -> DocumentText | None:
        return None


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def deps(gateway: FakeGateway) -> GraphDeps:
    return GraphDeps(
        user_id="u1",
        session_id="s1",
        models=None,  # type: ignore[arg-type]
        bus=None,  # type: ignore[arg-type]
        settings=RunSettings(300_000, 3, "fr", ("fr",), ""),
        session_factory=None,  # type: ignore[arg-type]
        memory=gateway,
    )
