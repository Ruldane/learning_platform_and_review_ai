"""État du parcours `quiz` (D100). Le quiz et les notes sont en base (port `QuizStore`) : l'état
ne garde que ce qui passe d'un nœud au suivant (le module, le brouillon de l'Examinateur, la
tentative, les notes à ranger) et ce qu'il faut annoncer."""

from typing import Any, TypedDict


class QuizState(TypedDict, total=False):
    mode: str  # `generate` : écrire le quiz ; `grade` : noter une tentative
    quiz_id: str | None
    attempt_id: str | None
    material: dict[str, Any]  # `ModuleMaterial` en JSON
    draft: dict[str, Any] | None  # `QuizDraft` en JSON ; None : quiz invalide après 3 essais
    failure: str  # raison de l'échec du quiz
    questions: int  # questions rangées
    attempt: dict[str, Any]  # `AttemptToGrade` en JSON
    grades: dict[str, list[Any]]  # ref → [note, retour], toutes les questions de la tentative
    graded: dict[str, Any]  # `GradedSaved` en JSON
    summary: str
