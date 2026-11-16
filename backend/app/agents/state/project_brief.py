"""État du parcours `project_brief` (D165). Les entrées du module sont en base, derrière le port
`ProjectStore` : chaque nœud les relit. L'état ne garde que l'identifiant du projet, l'énoncé écrit
(le temps d'aller du nœud `write` au nœud `save`, comme les propositions d'une revue de CV : une
donnée du projet dans les points de contrôle, jamais dans un journal) et le résumé de
`run.completed`."""

from typing import Any, Protocol, TypedDict


class ProjectBriefState(TypedDict, total=False):
    project_id: str
    brief: dict[str, Any]  # `ProjectBrief` en JSON
    summary: str  # résumé de `run.completed`


class Node(Protocol):
    """Forme d'un nœud (paramètre nommé `state`, comme l'attend `StateGraph.add_node`)."""

    async def __call__(self, state: ProjectBriefState) -> ProjectBriefState: ...
