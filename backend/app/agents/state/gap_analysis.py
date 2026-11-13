"""État du parcours `gap_analysis` (D121). L'offre, son analyse et l'écart sont en base (port
`GapStore`) : l'état ne garde que ce qui passe d'un nœud au suivant. Le texte de l'offre n'y
entre pas : `analyze` le relit par le port."""

from typing import Any, TypedDict


class GapAnalysisState(TypedDict, total=False):
    posting_id: str
    analysis: dict[str, Any] | None  # `PostingAnalysis` en JSON ; None : pas encore analysée
    reused: bool  # l'analyse était déjà rangée : l'Analyste ne l'a pas refaite
    rejection: str  # raison du refus sans appel au modèle (texte trop court)
    duplicates: list[dict[str, Any]]  # `DuplicateHit` en JSON (offre analysée ici)
    matches: list[dict[str, Any]]  # `SkillMatch` en JSON, un par besoin de l'offre
    saved: dict[str, Any]  # `GapSaved` en JSON
    summary: str
