"""État du parcours `interview` (D145). Le contexte vient du port (une seule lecture) ; le plan, la
question en cours et les échanges vivent dans l'état (checkpointer) jusqu'à `save`, la seule
écriture : une question en attente se reprend donc sans rien redemander au modèle."""

from typing import Any, TypedDict


class InterviewState(TypedDict, total=False):
    interview_id: str
    system_design: bool
    design_submission: dict[str, Any] | None
    design_review: dict[str, Any]
    context: dict[str, Any]  # `InterviewContext` en JSON
    plan: list[dict[str, Any]]  # `PlannedQuestion` en JSON, écrit une fois
    position: int  # rang de la question principale en cours (`len(plan)` : toutes posées)
    current: str  # le texte posé à January : la question, ou sa relance
    follow_up_open: bool  # `current` est la relance de la question principale en cours
    reply: dict[str, Any] | None  # `{"action": "answer" | "stop", "text"}` ; None : illisible
    exchanges: list[dict[str, Any]]  # `Exchange` en JSON, dans l'ordre du plan
    debrief: dict[str, Any] | None  # `Debrief` en JSON ; None : arrêté avant toute réponse
    flags: list[str]  # termes de la réponse améliorée que le profil ne dit pas
    cards: list[dict[str, Any]]  # `CardDraft` en JSON, une par question ratée
    summary: str
