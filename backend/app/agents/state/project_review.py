"""État du parcours `project_review` (D165). L'énoncé, le rendu et le profil sont en base, derrière
le port `ProjectStore` : chaque nœud les relit. L'état garde ce qui passe d'un nœud au suivant : le
texte du dépôt (lu une fois, le temps de la session), l'évaluation et les brouillons, en JSON.
Données du projet dans les points de contrôle, jamais dans un journal."""

from typing import Any, Literal, Protocol, TypedDict


class ProjectReviewState(TypedDict, total=False):
    project_id: str
    mode: Literal["review", "drafts"]  # `drafts` : seulement les brouillons d'un projet validé
    title: str  # titre de l'énoncé, pour `artifact.ready`
    repo_text: str | None  # le README lu, coupé à 8 000 caractères
    repo_status: Literal["read", "unreadable", "none"]
    nothing_to_read: bool  # ni description ni dépôt lisible : aucune évaluation
    first_drafts: dict[str, Any]  # `ProjectDrafts` du premier jet, relu par le nouvel essai
    retry_needed: bool  # un brouillon a des termes ou une longueur hors bornes
    outcome: dict[str, Any]  # `ReviewOutcome` en JSON (sans brouillons avant `drafts`)
    summary: str  # résumé de `run.completed`


class Node(Protocol):
    """Forme d'un nœud (paramètre nommé `state`, comme l'attend `StateGraph.add_node`)."""

    async def __call__(self, state: ProjectReviewState) -> ProjectReviewState: ...
