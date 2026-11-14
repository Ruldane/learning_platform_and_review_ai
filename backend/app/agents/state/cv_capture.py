"""État du parcours `cv_capture` (D124 ; mode `design` en 6.9). Le profil et ses sources sont des
données personnelles : l'état les garde le temps de la session (checkpoints), jamais un
journal."""

from typing import Any, TypedDict


class CvCaptureState(TypedDict, total=False):
    mode: str  # "profile" | "design"
    document_ids: list[str]
    note: str | None
    template_id: str | None
    sources: list[dict[str, str]]  # `ProfileSource` en JSON : {kind, text}
    hidden: list[str]  # lignes invisibles des PDF (preflight G6)
    draft: dict[str, Any]  # `MasterProfileData` en JSON, ids provisoires puis contrôlé
    dropped: list[str]  # texte des lignes et faits retirés, montré à January seule
    unsupported: int  # lignes retirées : chiffre introuvable
    untraced: int  # faits retirés : introuvables dans les documents
    version: int  # numéro du brouillon rangé
    summary: str
