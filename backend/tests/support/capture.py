"""Faux port de la capture rapide (`FakeCaptureStore`) en mémoire, idempotent comme le contrat, et
les liens de test (`capture_links`) : deux modules `m1`, `m2` et trois tâches `t1…t3`, dont les
ids (`task-id-t1`…) ne doivent jamais atteindre le modèle (F7). Aucun réseau ni LLM."""

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.agents.tools.capture_port import (
    CaptureDigest,
    CaptureMaterial,
    CaptureSource,
    CaptureStored,
    ProgramLinks,
)
from app.agents.tools.replan_port import ModuleRef, TaskRef
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError

TODAY = date(2026, 11, 18)
SUMMARY = [
    "L'attention pondère chaque mot selon les autres.",
    "Plusieurs têtes regardent des relations différentes.",
    "Les sorties des têtes sont concaténées puis projetées.",
    "Le coût croît avec le carré de la longueur.",
    "Les positions sont ajoutées aux plongements.",
]


def capture_links() -> ProgramLinks:
    return ProgramLinks(
        [
            ModuleRef("m1", "Transformers", ["Attention"], "module-id-m1"),
            ModuleRef("m2", "API de LLM", ["API de LLM"], "module-id-m2"),
        ],
        [
            TaskRef("t1", "Lire l'article sur l'attention", "lire", 40, TODAY, "m1", False,
                    "task-id-t1"),
            TaskRef("t2", "Regarder la vidéo sur les têtes", "regarder", 30, TODAY, "m1", False,
                    "task-id-t2"),
            TaskRef("t3", "Pratiquer un appel d'API", "pratiquer", 45, TODAY, "m2", False,
                    "task-id-t3"),
        ],
    )  # fmt: skip


def digest_reply(**over: Any) -> str:
    """Réponse JSON de l'Archiviste ; `over` remplace des champs (`summary`, `covered_task`…)."""
    data: dict[str, Any] = {
        "title": "L'attention multi-têtes",
        "summary": SUMMARY,
        "concepts": ["Attention", "Multi-têtes"],
        "modules": ["m1"],
        "covered_task": None,
        "learned": False,
        "flashcards": [],
    }
    return json.dumps(data | over, ensure_ascii=False)


def card(front: str, back: str = "Une réponse.") -> dict[str, Any]:
    return {"front": front, "back": back, "skill": "Attention"}


@dataclass(frozen=True)
class StoreCall:
    session_id: str
    digest: CaptureDigest
    material: CaptureMaterial
    links: ProgramLinks
    source: CaptureSource


@dataclass
class FakeCaptureStore:
    links_value: ProgramLinks = field(default_factory=capture_links)
    # Réponses successives de `document` par id (la dernière se répète) ; absent : 404.
    documents: dict[str, list[CaptureMaterial | None]] = field(default_factory=dict)
    document_calls: int = 0
    links_calls: int = 0
    store_calls: list[StoreCall] = field(default_factory=list)
    stored: dict[str, CaptureStored] = field(default_factory=dict)  # par session
    tick_calls: int = 0
    ticked: list[str] = field(default_factory=list)
    vanished: set[str] = field(default_factory=set)  # tâches retirées entre-temps
    card_calls: int = 0
    cards: dict[str, CardDraft] = field(default_factory=dict)  # par recto
    block_after_store: bool = False

    async def document(self, user_id: str, document_id: str) -> CaptureMaterial | None:
        self.document_calls += 1
        answers = self.documents.get(document_id)
        if answers is None:
            raise AppError("document_not_found", "Document introuvable.", 404)
        return answers.pop(0) if len(answers) > 1 else answers[0]

    async def links(self, user_id: str) -> ProgramLinks:
        self.links_calls += 1
        return self.links_value

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
        self.store_calls.append(StoreCall(session_id, digest, material, links, source))
        if session_id not in self.stored:
            covered = links.task(digest.covered_task) if digest.covered_task else None
            self.stored[session_id] = CaptureStored(
                f"item-{len(self.stored) + 1}", f"entry-{len(self.stored) + 1}", covered
            )
        if self.block_after_store:
            await asyncio.Event().wait()
        return self.stored[session_id]

    async def tick_task(self, user_id: str, session_id: str, task_id: str) -> bool:
        self.tick_calls += 1
        if task_id in self.vanished:
            return False
        if task_id not in self.ticked:
            self.ticked.append(task_id)
        return True

    async def add_cards(self, user_id: str, session_id: str, cards: Sequence[CardDraft]) -> int:
        self.card_calls += 1
        created = 0
        for one in cards:
            if one.front not in self.cards:
                self.cards[one.front] = one
                created += 1
        return created
