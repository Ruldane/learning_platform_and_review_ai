"""État du parcours `hiring_committee` (D147). Le contexte vient du port (une seule lecture) ; les
impressions, les tours, les votes et la synthèse vivent dans l'état (checkpointer) jusqu'à `save`,
la seule écriture : un nœud terminé n'est jamais refait, un vote donné n'est jamais redemandé."""

from typing import Any, TypedDict


class HiringCommitteeState(TypedDict, total=False):
    run_id: str
    context: dict[str, Any]  # `CommitteeContext` en JSON
    # Ce que les personas ont dit, dans l'ordre : `{"persona", "round", "text"}` ; le tour 0 est
    # la première impression, les tours 1 et 2 le débat.
    spoken: list[dict[str, Any]]
    votes: list[dict[str, Any]]  # `PersonaVote` en JSON, dans l'ordre des personas
    synthesis: dict[str, Any]  # `Synthesis` en JSON : verdict du code, objections, changements
    summary: str
