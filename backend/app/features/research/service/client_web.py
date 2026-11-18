"""Sources publiques rendues par le client qui joue l'Éclaireur."""

from urllib.parse import urlsplit

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.agents.prompts.loader import untrusted
from app.agents.runtime.played_model import PlayedModels
from app.agents.runtime.structured import structured_call
from app.core.domains import normalize_domain
from app.core.errors import AppError
from app.features.memory.service.upload import normalize_url
from app.features.research.service.cache import CachedPage
from app.features.research.service.chain import SearchRequest
from app.features.research.service.prefs import ResearchPrefs
from app.providers.search.base import MAX_RESULTS, SearchResult, keep_unique


def public_link(url: str) -> str:
    result = normalize_url(url)
    host = urlsplit(result).hostname or ""
    try:
        normalize_domain(host)
    except ValueError:
        raise AppError("invalid_web_source", "Indique un site web public.", 422) from None
    if host.endswith((".local", ".internal", ".localhost")):
        raise AppError("invalid_web_source", "Indique un site web public.", 422)
    return result


class ClientSearchHit(BaseModel):
    url: HttpUrl
    title: str = Field(default="", max_length=400)
    snippet: str = Field(default="", max_length=1000)
    published: str | None = Field(default=None, max_length=32)

    @field_validator("url")
    @classmethod
    def public(cls, url: HttpUrl) -> HttpUrl:
        try:
            public_link(str(url))
        except AppError:
            raise ValueError("indique un site web public") from None
        return url


class SearchSources(BaseModel):
    sources: list[ClientSearchHit] = Field(max_length=MAX_RESULTS)


class ReadSource(BaseModel):
    text: str = Field(default="", max_length=80_000)
    title: str | None = Field(default=None, max_length=400)
    author: str | None = Field(default=None, max_length=200)
    date: str | None = Field(default=None, max_length=32)
    lang: str | None = Field(default=None, max_length=8)


class ClientWeb:
    def __init__(self, user_id: str, client: str) -> None:
        self.user_id = user_id
        self.models = PlayedModels(client)

    async def search(self, request: SearchRequest, prefs: ResearchPrefs) -> list[SearchResult]:
        details = (
            f"Requête : {request.query}\nLangue : {request.lang or ', '.join(prefs.languages)}\n"
            f"Période : {request.time_range or 'sans limite'}\n"
            f"Domaines privilégiés : {', '.join(prefs.preferred)}\n"
            f"Domaines exclus : {', '.join(prefs.excluded)}"
        )
        model = await self.models.get_chat_model(self.user_id, "rapide", agent="scout")
        result = await structured_call(
            model,
            SearchSources,
            [
                SystemMessage(
                    "Cherche avec tes outils web publics et rends les résultats observés."
                ),
                HumanMessage(untrusted(details, "paramètres de recherche")),
            ],
            agent="scout",
            step="sources-web",
            intent="je recherche des sources publiques",
        )
        return keep_unique(
            [
                SearchResult(
                    hit.title, public_link(str(hit.url)), hit.snippet, "mcp", hit.published
                )
                for hit in result.sources
            ]
        )

    async def read(self, url: str) -> CachedPage:
        public_link(url)
        model = await self.models.get_chat_model(self.user_id, "rapide", agent="scout")
        result = await structured_call(
            model,
            ReadSource,
            [
                SystemMessage(
                    "Lis cette page avec tes outils web publics. Rends son texte visible et "
                    "ses métadonnées. Si elle est inaccessible, laisse le texte vide."
                ),
                HumanMessage(untrusted(url, "adresse à lire")),
            ],
            agent="scout",
            step="lecture-web",
            intent="je lis une source publique",
        )
        if not result.text.strip():
            return CachedPage(
                "unreadable", result.title, "", None, None, None, "Page inaccessible."
            )
        return CachedPage(
            "ok",
            result.title,
            result.text,
            result.author,
            result.date,
            result.lang,
            None,
        )
