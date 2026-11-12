"""Matériel de test de la recherche web : fournisseurs factices (aucun SearXNG ni Brave réel)."""

from app.core.providers import ResearchProviders
from app.providers.search.base import SearchProvider
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebReader


def fake_research_providers(
    web: WebReader, *, searxng: FakeSearch | None = None, brave: FakeSearch | None = None
) -> ResearchProviders:
    """`FakeSearch` vides par défaut ; la fabrique Brave rend toujours le même faux, quelle que
    soit la clé ; `web` est le lecteur des fournisseurs de la mémoire (le même qu'en vrai)."""
    brave_search = brave if brave is not None else FakeSearch("brave")

    def brave_factory(api_key: str) -> SearchProvider:
        return brave_search

    return ResearchProviders(
        searxng=searxng if searxng is not None else FakeSearch("searxng"),
        brave=brave_factory,
        web=web,
    )
