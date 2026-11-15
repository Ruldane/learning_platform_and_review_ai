"""État du parcours `cv_review` (D129). L'offre, le profil, le CV d'origine et la revue sont en
base (port `CvReviewStore`) : chaque nœud relit le contexte par `context` (lecture seule) et l'état
ne garde que ce qui passe d'un nœud au suivant. Le texte de l'offre n'y entre pas. Les
propositions (textes du CV) sont des données personnelles : l'état les garde le temps de la
session (checkpoints), jamais un journal."""

from typing import Any, TypedDict


class CvReviewState(TypedDict, total=False):
    review_id: str
    posting_id: str
    analysis: dict[str, Any] | None  # `PostingAnalysis` en JSON ; None : pas encore analysée
    reused: bool  # écrit par le nœud `analyze` de l'Analyste (6.5)
    rejection: str  # idem : texte trop court
    duplicates: list[dict[str, Any]]  # écrit par `save_analysis` de l'Analyste (non utilisé)
    company: str | None  # nom de l'entreprise (offre), `None` : inconnue
    company_brief: dict[str, Any] | None  # `CompanyBrief` en JSON
    ats: str | None  # ATS repéré par le domaine d'un lien
    ats_notes: list[str]  # notes du Lecteur ATS (rapport)
    strengths: list[str]  # forces vues par le Recruteur (rapport)
    risks: list[str]  # risques vus par le Recruteur (rapport)
    proposals: list[dict[str, Any]]  # `Proposal` en JSON, texte courant (amendements compris)
    # réf. → {stance, reason[, original]} de l'autre agent au tour 1 (original : avant `amend`)
    contested: dict[str, dict[str, str]]
    removed: list[str]  # réf. retirées au tour 2 : l'auteur a dit `drop`
    items: list[dict[str, Any]]  # {proposal, status, blocks} après le validateur
    # mots clés de l'offre que les faits cités ne portent pas : à appuyer par un fait ou à acquérir
    gap_terms: list[str]
    saved: int  # modifications rangées
    output: dict[str, Any] | None  # réponse analysée de la question `cv_output`
    summary: str
