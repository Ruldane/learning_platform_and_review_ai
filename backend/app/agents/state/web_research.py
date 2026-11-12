"""État du parcours `web_research` : de la question aux sources notées et retenues en mémoire."""

from typing import Any, TypedDict


class WebResearchState(TypedDict, total=False):
    query: str
    urls: list[str]  # pages à lire en plus des résultats (essai, contrôle)
    queries: list[dict[str, Any]]  # `PlannedQuery.model_dump()`, tronquées au plafond
    hits: list[dict[str, Any]]  # {url, title, preferred}, privilégiés d'abord
    pages: list[dict[str, Any]]  # pages lisibles à noter (texte rogné pour la notation)
    unreadable: int  # pages illisibles (déjà signalées par `source.found`)
    verdicts: list[dict[str, Any]]  # une entrée par page notée
    remembered: int  # sources retenues écrites en mémoire (rien d'écrit si déjà là)
    summary: str
