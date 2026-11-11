"""Port de la mémoire pour les agents (D68). `app.agents` n'importe aucune feature (contrat 6) :
il décrit ici ce dont il a besoin, la composition (`app.bootstrap.memory_gateway`) branche
l'implémentation de la feature `memory`, comme pour `RunSettingsSource`.

Tout texte rendu à un agent (`agent_text`) encadre les contenus importés par `untrusted()` (17.4).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.core.errors import AppError

# Types qu'un agent peut écrire : jamais un `document` (réservé à l'import).
AgentWritableKind = Literal["acquis", "lecon", "source", "offre", "decision"]
NO_SKILLS = "Aucun acquis en mémoire."


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
    level: Literal["declare", "en_cours"] | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class WriteResult:
    item_id: str
    kind: str
    title: str
    status: Literal["active", "pending"]
    created: bool  # faux : le même contenu était déjà en mémoire (rien d'écrit)


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
        """« Acquis (3) :\n- Python — declare\n… » ; titres ramenés sur une ligne."""
        if not self.skills:
            return NO_SKILLS
        lines = [f"Acquis ({self.total}) :"]
        lines += [f"- {_one_line(skill.title)} — {skill.level}" for skill in self.skills]
        return "\n".join(lines)


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
    return AppError("memory_unavailable", "La mémoire n'est pas branchée sur ce moteur.", 503)


class _NoMemory:
    """Valeur par défaut du moteur (tests existants, démarrages sans mémoire)."""

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
