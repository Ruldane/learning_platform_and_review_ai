"""État du parcours `study_session` (D102). La leçon vient du port (`StudyContext`, une seule
lecture) ; seule la fin de session est écrite, par le port, dans `wrap_up`. L'état garde la
position dans la séance (phase, rang), la question en cours et ses indices, et le sort de chaque
question (`outcomes`)."""

from typing import Any, TypedDict


class StudySessionState(TypedDict, total=False):
    study_session_id: str
    context: dict[str, Any]  # `StudyContext` en JSON (sections et sources en dictionnaires)
    memory: str  # contexte mémoire du Tuteur, déjà encadré par le port
    # Position : `section` (rang de la section), `exercise` (0), `final` (rang 0…2), `done`
    phase: str
    index: int
    finals: list[dict[str, str]]  # {question, expected} : les 3 questions finales, écrites une fois
    question: str  # question en cours (posée par `ask`)
    expected: str  # sa réponse attendue (le corrigé de la leçon pour l'exercice)
    hints: int  # indices donnés pour la question en cours
    given_hints: list[str]  # leur texte, pour graduer le suivant
    reply: dict[str, Any] | None  # `TutorAnswer` en JSON ; None : réponse illisible
    outcomes: list[dict[str, Any]]  # `Outcome` en JSON, dans l'ordre
    last_input_seq: int  # dernier `user.message` lu
    board_step: int  # dernier numéro d'étape du tableau du Tuteur
    ended_early: bool  # « Terminer » avant la dernière question
    session_summary: str  # résumé du Tuteur (`SessionSummary`)
    finished: dict[str, Any]  # `StudyFinished` en JSON
    summary: str  # résumé de `run.completed`
