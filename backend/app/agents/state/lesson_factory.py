"""État du parcours `lesson_factory` (D90). Il hérite de l'état de l'Éclaireur : ses nœuds
entrent dans le parcours tels quels, nœud pour nœud (mêmes clés, mêmes points de contrôle que
`web_research`). La leçon elle-même n'est écrite en base qu'à la publication (port
`LessonStore`) : l'état garde le brouillon, ses contrôles et les ressources choisies."""

from typing import Any

from app.agents.state.web_research import WebResearchState


class LessonFactoryState(WebResearchState, total=False):
    program_id: str
    module_id: str
    brief: dict[str, Any]  # `ModuleBrief` en JSON
    resources: list[
        dict[str, Any]
    ]  # `ResourcePick` en JSON : 3 à 6, moins si le web n'en donne pas
    resource_notes: list[str]  # remarques sans gravité (ressources insuffisantes)
    draft: str  # Markdown du Rédacteur
    revisions: int  # révisions déjà demandées au Rédacteur (0 : première version)
    words: int  # mots du brouillon, blocs de code exclus
    problems: list[str]  # contrôles déterministes non satisfaits (phrases françaises)
    unsupported: list[str]  # affirmations non sourcées relevées par le Vérificateur
    published: dict[str, Any]  # `PublishedLesson` en JSON
    failure: str  # raison de l'échec de la leçon
    next_module: str | None  # module dont la leçon vient d'être lancée par la chaîne
