"""Port de la capture rapide (SPEC F18, D108). `app.agents` n'importe aucune feature (contrat 6) :
il décrit ici ce dont le parcours `capture` a besoin (un document importé, les liens vers le
programme, le rangement de la capture, la tâche cochée, les fiches) ; la feature `capture`
l'implémente (`AgentCaptureStore`).

L'Archiviste relie la capture au programme par références (`m3`, `t12`) : les ids réels
(`ModuleRef.module_id`, `TaskRef.task_id`) ne sont jamais montrés au modèle (F7). Le parcours
garde l'instantané des liens dans son état ; `store` reçoit cet instantané et `tick_task` l'id
résolu sur lui.

Chaque écriture est idempotente : `store` par session (ligne de journal « capture:{session} »),
`tick_task` (une tâche faite le reste), `add_cards` (dédoublonnées par recto). Un nœud rejoué
après un arrêt (SPEC 9.4) n'écrit jamais rien de plus.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.prose import ShortenToMax
from app.agents.tools.replan_port import MODULE_REF, TASK_REF, ModuleRef, TaskRef
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError

CaptureSource = Literal["url", "text", "document"]
SUMMARY_LINES = 5

SummaryLine = Annotated[str, Field(max_length=200), ShortenToMax()]
ConceptName = Annotated[str, Field(min_length=2, max_length=120)]
ModuleRefText = Annotated[str, Field(pattern=MODULE_REF)]


@dataclass(frozen=True)
class CaptureMaterial:
    """Ce que l'Archiviste lit : la page, le document ou le texte de January. `url` : l'adresse
    lue (normalisée), celle d'un document importé par lien, sinon `None`."""

    title: str
    text: str
    url: str | None


class CaptureDigest(BaseModel):
    """La capture résumée par l'Archiviste (sortie structurée)."""

    title: str = Field(min_length=3, max_length=120)
    summary: list[SummaryLine] = Field(min_length=1, max_length=SUMMARY_LINES)
    concepts: list[ConceptName] = Field(default_factory=list, max_length=10)
    modules: list[ModuleRefText] = Field(default_factory=list, max_length=5)
    covered_task: str | None = Field(default=None, pattern=TASK_REF)
    learned: bool = False  # « j'ai appris X » : concepts → acquis `declare` (note de January)
    flashcards: list[CardDraft] = Field(default_factory=list, max_length=5)


@dataclass(frozen=True)
class ProgramLinks:
    """Modules des programmes validés et tâches à faire à ± 7 jours (jour de January)."""

    modules: list[ModuleRef]
    tasks: list[TaskRef]

    def module(self, ref: str) -> ModuleRef | None:
        return next((m for m in self.modules if m.ref == ref), None)

    def task(self, ref: str) -> TaskRef | None:
        return next((t for t in self.tasks if t.ref == ref), None)


NO_LINKS = ProgramLinks([], [])


@dataclass(frozen=True)
class CaptureStored:
    memory_item_id: str
    journal_entry_id: str
    covered_task: TaskRef | None  # la tâche que la capture couvre, résolue sur `links`


class CaptureStore(Protocol):
    async def document(self, user_id: str, document_id: str) -> CaptureMaterial | None:
        """Le document importé de January ; `None` : pas encore indexé. 404
        `document_not_found` s'il n'est pas à elle, 409 `document_failed` si son import a
        échoué (il ne sera jamais indexé)."""
        ...

    async def links(self, user_id: str) -> ProgramLinks: ...

    async def store(
        self,
        user_id: str,
        session_id: str,
        digest: CaptureDigest,
        material: CaptureMaterial,
        links: ProgramLinks,
        *,
        source: CaptureSource,
    ) -> CaptureStored:
        """Élément de mémoire `document` résumé, acquis `declare` si `learned`, ligne de
        journal `capture` ; idempotent par session (un rejeu relit ce qui est rangé)."""
        ...

    async def tick_task(self, user_id: str, session_id: str, task_id: str) -> None:
        """Coche la tâche (idempotent ; une tâche d'une autre est ignorée)."""
        ...

    async def add_cards(self, user_id: str, session_id: str, cards: Sequence[CardDraft]) -> int:
        """Fiches de la capture, dédoublonnées par recto ; rend le nombre créé."""
        ...


def capture_unavailable() -> AppError:
    return AppError("capture_unavailable", "La capture n'est pas branchée sur ce moteur.", 503)


class _NoCapture:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def document(self, user_id: str, document_id: str) -> CaptureMaterial | None:
        raise capture_unavailable()

    async def links(self, user_id: str) -> ProgramLinks:
        raise capture_unavailable()

    async def store(
        self,
        user_id: str,
        session_id: str,
        digest: CaptureDigest,
        material: CaptureMaterial,
        links: ProgramLinks,
        *,
        source: CaptureSource,
    ) -> CaptureStored:
        raise capture_unavailable()

    async def tick_task(self, user_id: str, session_id: str, task_id: str) -> None:
        raise capture_unavailable()

    async def add_cards(self, user_id: str, session_id: str, cards: Sequence[CardDraft]) -> int:
        raise capture_unavailable()


NO_CAPTURE: CaptureStore = _NoCapture()
