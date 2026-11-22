"""Une question et deux pages générées pour la recette du débat."""

from app.providers.search.base import SearchResult
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from tests.support.memory import FakeWebReader

QUESTION = "Quel tri stable choisir pour un petit jeu de données ?"
METHOD = "https://sources-debat.example.test/methode"
PRACTICE = "https://sources-debat.example.test/pratique"
JUDGMENT = "Je choisis le tri stable et je vérifierai la taille des données."


def expert_scripts() -> dict[str, list[str]]:
    return {
        "scout": ["L’étude fictive compare deux tris stables [1]."],
        "practitioner": ["En pratique, je partirais de l’exemple du guide [2]."],
        "skeptic": ["La taille du jeu de données change le choix [1, 99]."],
    }


def script_expert_sources(web: FakeWebReader, search: FakeSearch) -> None:
    sources = (
        (METHOD, "Méthode de comparaison", "Un texte fictif sur deux algorithmes de tri stable."),
        (PRACTICE, "Guide pratique", "Un exemple fictif avec de petites listes et leurs mesures."),
    )
    for url, title, body in sources:
        web.pages[url] = WebDocument(url, title, body, None, None, "fr", None)
    search.results[QUESTION] = [
        SearchResult(title, url, body, search.name, None) for url, title, body in sources
    ]
