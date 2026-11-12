"""État du parcours `program_builder` (D86). Le plan lui-même est en base (port `ProgramStore`),
pas ici : l'état ne garde que le contexte du prompt, le dernier brouillon du Stratège (à passer au
nœud `save`), les références de la version enregistrée et la réponse de January."""

from typing import Any, TypedDict


class ProgramState(TypedDict, total=False):
    goal_id: str
    proposal_ids: list[str]  # une proposition choisie, ou deux pour un mélange
    start_date: str | None  # ISO ; `None` : prochain lundi (choisi par le port)
    plan_vars: dict[str, Any]  # variables du prompt `plan`, tirées du contexte du port
    revision: int  # 0 : première version ; +1 à chaque révision demandée par January
    note: str  # note de révision de January (vide pour la première version)
    draft: dict[str, Any]  # `PlanDraft` en JSON : le dernier brouillon du Stratège
    saved: dict[str, Any]  # `DraftSaved` en JSON : la version enregistrée
    validation: dict[str, Any] | None  # `ValidationAnswer` en JSON ; None : réponse invalide
    summary: str
