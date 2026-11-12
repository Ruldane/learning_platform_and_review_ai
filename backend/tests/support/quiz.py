"""Faux port des quiz (`FakeQuizStore`) en mémoire, idempotent comme le contrat, et fabriques de
brouillons de quiz (`quiz_draft`) et de tentatives pour les tests du parcours `quiz`. Aucun
réseau ni LLM."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.quiz_port import (
    AttemptToGrade,
    GradedSaved,
    GradingItem,
    ModuleMaterial,
    QuizDraft,
)
from app.core.errors import AppError
from app.features.quiz.service.scoring import passed, score_percent

QUIZ_ID = "cccccccc-bbbb-cccc-dddd-000000000001"
ATTEMPT_ID = "cccccccc-bbbb-cccc-dddd-000000000002"
TITLE = "Attention multi-têtes"
LESSON = "# Attention multi-têtes\n\nLa softmax transforme des scores en poids qui somment à 1."
TYPES = ("qcm", "short", "code", "explain")


def question(type_: str, number: int, **over: Any) -> dict[str, Any]:
    """Une question valide de `type_` ; `over` remplace des champs."""
    found: dict[str, Any] = {
        "type": type_,
        "prompt": f"Question {number} : que fait la fonction softmax dans l'attention ?",
        "expected": "Elle transforme les scores en poids positifs qui somment à 1.",
        "rubric": ["Parle de poids positifs.", "Dit que la somme vaut 1."],
        "explanation": "La softmax normalise les scores d'attention en une distribution.",
        "skill": "Attention",
    }
    if type_ == "qcm":
        found |= {"choices": ["Elle normalise", "Elle trie", "Elle filtre"], "correct_index": 0}
    if type_ == "code":
        found["code"] = "def double(x):\n    return x * 2"
    return found | over


def card(number: int) -> dict[str, Any]:
    return {
        "front": f"Fiche {number} : à quoi sert la softmax ?",
        "back": "À normaliser des scores en poids.",
        "skill": "Attention",
    }


def quiz_draft(
    types: tuple[str, ...] = TYPES, count: int = 10, cards: int = 4, **over: Any
) -> dict[str, Any]:
    """Un brouillon de `count` questions qui tournent sur `types`, et `cards` fiches."""
    questions = [question(types[n % len(types)], n + 1) for n in range(count)]
    flashcards = [card(n + 1) for n in range(cards)]
    return {"title": f"Quiz : {TITLE}", "questions": questions, "flashcards": flashcards} | over


def open_item(ref: str, type_: str = "explain", answer: str = "Poids sommant à 1.") -> GradingItem:
    return GradingItem(
        ref=ref,
        type=type_,  # type: ignore[arg-type]
        prompt=f"Énoncé de {ref} : explique la softmax.",
        code="def double(x):\n    return x * 2" if type_ == "code" else None,
        expected="Des poids positifs qui somment à 1.",
        rubric=["Parle de poids.", "Dit que la somme vaut 1."],
        answer=answer,
    )


@dataclass
class FakeQuizStore:
    """`materials` / `attempts` : (utilisateur, id) → donnée ; celle d'un autre utilisateur est
    introuvable (404). `saved` : quiz rangés (rejoué : le premier reste) ; `failed` : quiz →
    raison ; `grades` / `graded` : tentative → notes reçues / note rendue (rejoué : la première).
    `block_after_save_grades` fige l'appel après l'écriture (arrêt du back en plein nœud)."""

    materials: dict[tuple[str, str], ModuleMaterial] = field(default_factory=dict)
    saved: dict[str, QuizDraft] = field(default_factory=dict)
    save_calls: int = 0
    failed: dict[str, str] = field(default_factory=dict)
    attempts: dict[tuple[str, str], AttemptToGrade] = field(default_factory=dict)
    grades: dict[str, dict[str, tuple[float, str]]] = field(default_factory=dict)
    graded: dict[str, GradedSaved] = field(default_factory=dict)
    save_grades_calls: int = 0
    block_after_save_grades: bool = False

    def add_material(self, user_id: str, *, lesson: str = LESSON) -> ModuleMaterial:
        found = ModuleMaterial(QUIZ_ID, TITLE, ["Attention", "Transformers"], lesson, "fr")
        self.materials[(user_id, QUIZ_ID)] = found
        return found

    def add_attempt(
        self,
        user_id: str,
        open_items: list[GradingItem] | None = None,
        qcm_points: dict[str, float] | None = None,
        lesson: str = LESSON,
    ) -> AttemptToGrade:
        items = (
            open_items
            if open_items is not None
            else [open_item("q2", "short"), open_item("q3", "code"), open_item("q4")]
        )
        points = qcm_points if qcm_points is not None else {"q1": 1.0, "q5": 0.0}
        found = AttemptToGrade(ATTEMPT_ID, TITLE, items, points, lesson)
        self.attempts[(user_id, ATTEMPT_ID)] = found
        return found

    async def material(self, user_id: str, quiz_id: str) -> ModuleMaterial:
        found = self.materials.get((user_id, quiz_id))
        if found is None:
            raise AppError("quiz_not_found", "Quiz introuvable.", 404)
        return found

    async def save_quiz(self, user_id: str, session_id: str, quiz_id: str, draft: QuizDraft) -> int:
        await self.material(user_id, quiz_id)
        self.save_calls += 1
        self.saved.setdefault(quiz_id, draft)
        return len(self.saved[quiz_id].questions)

    async def quiz_failed(self, user_id: str, quiz_id: str, reason: str) -> None:
        await self.material(user_id, quiz_id)
        self.failed.setdefault(quiz_id, reason)

    async def attempt(self, user_id: str, attempt_id: str) -> AttemptToGrade:
        found = self.attempts.get((user_id, attempt_id))
        if found is None:
            raise AppError("attempt_not_found", "Tentative introuvable.", 404)
        return found

    async def save_grades(
        self,
        user_id: str,
        session_id: str,
        attempt_id: str,
        grades: Mapping[str, tuple[float, str]],
    ) -> GradedSaved:
        await self.attempt(user_id, attempt_id)
        self.save_grades_calls += 1
        if attempt_id not in self.graded:
            self.grades[attempt_id] = dict(grades)
            score = score_percent([points for points, _ in grades.values()])
            misses = sum(1 for points, _ in grades.values() if points < 1)
            self.graded[attempt_id] = GradedSaved(
                attempt_id, score, passed(score), misses, 0 if passed(score) else 2
            )
        if self.block_after_save_grades:
            await asyncio.Event().wait()
        return self.graded[attempt_id]
