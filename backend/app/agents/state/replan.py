"""État du parcours `replan` (D105). Le plan est en base (port `ReplanStore`) : l'état garde
l'instantané du contexte (les références `t12`, `m3` et leurs ids, F7), l'option choisie, le
dernier brouillon du Stratège (à passer au nœud `preview`), la version proposée et la réponse de
January."""

from typing import Any, TypedDict


class ReplanState(TypedDict, total=False):
    program_id: str
    trigger: str  # `weekly_review` ou `message`
    review_entry_id: str | None
    available_minutes: int | None
    message: str | None
    context: dict[str, Any]  # `ReplanContext` en JSON (dates ISO) : l'instantané des références
    option: str | None  # option choisie par January ; None : aucune (ou réponse invalide)
    revision: int  # 0 : première proposition ; +1 à chaque révision ou proposition périmée
    note: str  # note de révision de January (vide sinon)
    stale: bool  # la proposition précédente était périmée (lignes changées)
    draft: dict[str, Any]  # `ReplanDraft` en JSON : le dernier brouillon, droits appliqués
    preview: dict[str, Any]  # `PreviewSaved` en JSON : la version proposée
    answer: dict[str, Any] | None  # `AcceptAnswer` en JSON ; None : réponse invalide
    hint: str  # aide ajoutée à la question d'acceptation reposée (note vide, D106)
    outcome: str  # `empty`, `impossible`, `accepted`, `refused` : la fin du parcours
    summary: str
