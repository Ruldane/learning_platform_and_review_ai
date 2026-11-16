"""État du parcours `daily_brief` (D161). Ce qui est rangé (ressource, conseil) est en base,
derrière le port `BriefStore` : chaque nœud relit `context` et saute sa rubrique si elle est déjà
rangée (SPEC 9.4). L'état ne garde que l'identifiant du brief et le résumé de `run.completed` :
ni sujet, ni fait, ni texte (jamais d'une donnée de l'utilisatrice dans un point de contrôle)."""

from typing import Protocol, TypedDict


class DailyBriefState(TypedDict, total=False):
    brief_id: str
    summary: str  # résumé de `run.completed`


class Node(Protocol):
    """Forme d'un nœud (paramètre nommé `state`, comme l'attend `StateGraph.add_node`)."""

    async def __call__(self, state: DailyBriefState) -> DailyBriefState: ...
