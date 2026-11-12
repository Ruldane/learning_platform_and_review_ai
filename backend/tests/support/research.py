"""Matériel de test de la recherche web : fournisseurs factices (aucun SearXNG ni Brave réel)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.errors import AppError
from app.core.providers import ResearchProviders
from app.providers.search.base import SearchProvider
from app.providers.search.fake import FakeSearch
from app.providers.web.base import (
    ALLOWED_CONTENT_TYPES,
    FetchedResource,
    UrlUnsupported,
    WebFetcher,
    WebReader,
)


@dataclass
class FakeFetcher:
    """`WebFetcher` factice : `files` : URL → (type de contenu, corps) ou erreur levée ; toute
    autre URL lève `UrlUnsupported` (rien à télécharger). Un type hors de `content_types` est
    refusé comme le vrai fetcher. Note chaque URL demandée."""

    files: dict[str, tuple[str, bytes] | AppError] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    async def fetch(
        self,
        url: str,
        *,
        content_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES,
        headers: Mapping[str, str] | None = None,
    ) -> FetchedResource:
        self.calls.append(url)
        found = self.files.get(url)
        if found is None:
            raise UrlUnsupported()
        if isinstance(found, AppError):
            raise found
        content_type, body = found
        if content_type not in content_types:
            raise UrlUnsupported()
        return FetchedResource(url, url, content_type, body)


def fake_research_providers(
    web: WebReader,
    *,
    searxng: FakeSearch | None = None,
    brave: FakeSearch | None = None,
    fetcher: WebFetcher | None = None,
) -> ResearchProviders:
    """`FakeSearch` vides par défaut ; la fabrique Brave rend toujours le même faux, quelle que
    soit la clé ; `web` est le lecteur des fournisseurs de la mémoire (le même qu'en vrai) ;
    `fetcher` : `FakeFetcher` vide par défaut (aucun PDF téléchargeable)."""
    brave_search = brave if brave is not None else FakeSearch("brave")

    def brave_factory(api_key: str) -> SearchProvider:
        return brave_search

    return ResearchProviders(
        searxng=searxng if searxng is not None else FakeSearch("searxng"),
        brave=brave_factory,
        web=web,
        fetcher=fetcher if fetcher is not None else FakeFetcher(),
    )
