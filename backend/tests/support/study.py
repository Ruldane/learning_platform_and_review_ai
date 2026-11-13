"""Faux port des sessions d'étude (`FakeStudyStore`) en mémoire, idempotent comme le contrat, la
séance de test (`study_context`) et une mémoire factice (`FakeStudyMemory`) pour le parcours
`study_session`. Aucun réseau ni LLM."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from app.agents.runtime.speech import CitationEntry
from app.agents.tools.memory_port import (
    AgentWrite,
    DocumentText,
    MemoryHitView,
    MemorySearchResult,
    SkillEntry,
    SkillsSummary,
    WriteResult,
)
from app.agents.tools.study_port import (
    LessonSection,
    StudyContext,
    StudyFinished,
    StudyOutcome,
)
from app.core.errors import AppError

STUDY_ID = "dddddddd-bbbb-cccc-dddd-000000000001"
MODULE = "Attention multi-têtes"
SECTION_TEXTS = (
    "La softmax transforme des scores en poids qui somment à 1.",
    "Chaque tête apprend sa propre projection des requêtes et des clés.",
)
EXERCISE = "Calcule la softmax de [1, 2] et explique le résultat."
SOLUTION = "Environ [0,27 ; 0,73] : la plus grande valeur reçoit le plus de poids."
MEMORY_MARK = "Souvenir de January : elle connaît NumPy."


def study_context(
    *, mode: str = "socratic", sections: int = 2, question: str | None = None, **over: Any
) -> StudyContext:
    found = StudyContext(
        study_session_id=STUDY_ID,
        module_title=MODULE,
        mode=mode,  # type: ignore[arg-type]
        objectives=["Expliquer la softmax", "Lire une tête d'attention"],
        sections=[
            LessonSection(title, SECTION_TEXTS[n % 2])
            for n, title in enumerate(("L'essentiel en 5 lignes", "Explication")[:sections])
        ],
        exercise=EXERCISE,
        solution=SOLUTION,
        sources=[
            CitationEntry(1, "Attention Is All You Need", "https://arxiv.org/abs/1706.03762"),
            CitationEntry(2, "The Illustrated Transformer", "https://jalammar.github.io/x"),
        ],
        question=question,
    )
    return replace(found, **over)


@dataclass
class FakeStudyStore:
    """`contexts` : (utilisateur, étude) → séance ; celle d'un autre est introuvable (404).
    `finished` : la première fin reçue (rejouée : la première reste) ; `finish_calls` compte les
    appels ; `block_after_finish` fige l'appel après l'écriture (arrêt du back en plein nœud)."""

    contexts: dict[tuple[str, str], StudyContext] = field(default_factory=dict)
    finished: StudyOutcome | None = None
    finish_calls: int = 0
    block_after_finish: bool = False
    result: StudyFinished = field(
        default_factory=lambda: StudyFinished(
            minutes=42,
            tasks_done=["Lire la leçon"],
            flashcards_created=2,
            skills=[("Attention", "en_cours")],
        )
    )

    def add(self, user_id: str, context: StudyContext | None = None) -> StudyContext:
        found = context or study_context()
        self.contexts[(user_id, found.study_session_id)] = found
        return found

    async def context(self, user_id: str, study_session_id: str) -> StudyContext:
        found = self.contexts.get((user_id, study_session_id))
        if found is None:
            raise AppError("study_session_not_found", "Session d'étude introuvable.", 404)
        return found

    async def finish(
        self, user_id: str, session_id: str, study_session_id: str, outcome: StudyOutcome
    ) -> StudyFinished:
        await self.context(user_id, study_session_id)
        self.finish_calls += 1
        if self.finished is None:
            self.finished = outcome
        if self.block_after_finish:
            await asyncio.Event().wait()
        return self.result


@dataclass
class FakeStudyMemory:
    """Mémoire factice : un acquis et un fragment repérable (`MEMORY_MARK`) par recherche."""

    searches: list[str] = field(default_factory=list)

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None, k: int
    ) -> MemorySearchResult:
        self.searches.append(query)
        hit = MemoryHitView("i1", "c1", "document", "Notes", MEMORY_MARK, 0.8, "user")
        return MemorySearchResult([hit], MEMORY_MARK)

    async def write(
        self, user_id: str, session_id: str, author: str, write: AgentWrite
    ) -> WriteResult:
        raise AssertionError("Le Tuteur n'écrit pas en mémoire.")

    async def skills(self, user_id: str) -> SkillsSummary:
        return SkillsSummary(1, {"declare": 1}, [SkillEntry("a1", "Python", "declare", [])])

    async def document_text(
        self, user_id: str, document_id: str, *, max_chunks: int
    ) -> DocumentText | None:
        return None
