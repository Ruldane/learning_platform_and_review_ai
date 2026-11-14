"""État du parcours `cv_capture` (D124, D125). Le profil, ses sources et le contenu du CV sont des
données personnelles : l'état les garde le temps de la session (checkpoints), jamais un journal.
Les images des pages ne sont **jamais** dans l'état (relues par le port à chaque nœud qui les
montre au Maquettiste) : chaque checkpoint reste léger."""

from typing import Any, TypedDict


class CvCaptureState(TypedDict, total=False):
    mode: str  # "profile" | "design"
    document_ids: list[str]
    note: str | None
    template_id: str | None
    # Mode `profile` (Archiviste)
    sources: list[dict[str, str]]  # `ProfileSource` en JSON : {kind, text}
    hidden: list[str]  # lignes invisibles des PDF (preflight G6)
    draft: dict[str, Any]  # `MasterProfileData` en JSON, ids provisoires puis contrôlé
    dropped: list[str]  # texte des lignes et faits retirés, montré à January seule
    unsupported: int  # lignes retirées : chiffre introuvable
    untraced: int  # faits retirés : introuvables dans les documents
    version: int  # numéro du brouillon rangé
    summary: str
    # Mode `design` (Maquettiste)
    selectable: bool  # faux : CV scanné
    page_count: int
    sample: dict[str, Any]  # `CvContent` en JSON : contenu de démonstration
    spec: dict[str, Any]  # `TemplateSpec` en JSON : description courante
    pass_no: int  # dernière passe rendue (1 à 3 automatiques, puis une par ajustement)
    score: int  # score de la dernière passe
    kept_pass: int  # passe gardée par le port (`keeps_pass`) : la meilleure, D125
    kept_score: int  # score de la passe gardée : celui que January valide
    kept_spec: dict[str, Any]  # description de la passe gardée : « Ajuster » repart d'elle
    stalled: bool  # la dernière correction n'a pas donné de description valable
    adjustments: int  # ajustements demandés par January (5 au plus)
    instruction: str | None  # dernière consigne de January (500 caractères au plus)
    answer: dict[str, Any] | None  # réponse analysée de la question `cv_template`
