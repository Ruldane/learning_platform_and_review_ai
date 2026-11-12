"""Port de la recherche web pour les agents (D77). `app.agents` n'importe aucune feature
(contrat 6) : il décrit ici ce dont il a besoin, la composition (`app.bootstrap.web_gateway`)
branche l'implémentation de la feature `research`, comme pour la mémoire (`MemoryGateway`, D68).

Tout texte venu du web (titre, extrait, page) est du contenu non fiable : les outils
(`web_tools`) l'encadrent par `untrusted()` avant de le rendre à un modèle (17.4).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.errors import AppError

# Codes d'erreur de la feature `research` que le moteur reconnaît (le moteur n'importe pas la
# feature) ; un test de la passerelle vérifie qu'ils sont ceux de la feature.
QUOTA_CODE = "web_quota_reached"
SEARCH_UNAVAILABLE_CODE = "search_unavailable"

# Barème de la note d'une source (SPEC 10.3) : points maximaux par critère, 100 au total.
CRITERIA_MAX: dict[str, int] = {
    "authority": 30,
    "freshness": 20,
    "depth": 20,
    "author": 15,
    "pedagogy": 15,
}
KEEP_THRESHOLD = 60


@dataclass(frozen=True)
class WebHit:
    title: str
    url: str
    snippet: str
    engine: str
    published: str | None
    preferred: bool  # domaine privilégié dans les réglages


@dataclass(frozen=True)
class WebSearchResult:
    query: str  # la requête NETTOYÉE de toute donnée personnelle, celle qui a été envoyée
    provider: str | None
    hits: list[WebHit]


@dataclass(frozen=True)
class SourceVerdictView:
    source_id: str
    score: int | None  # `None` : note impossible à établir (sortie du modèle invalide, délai)
    verdict: Literal["kept", "rejected"]
    reason: str
    summary: str = ""  # résumé de la notation, repris tel quel quand le verdict est rejoué (D82)


@dataclass(frozen=True)
class PageRead:
    # `None` pour une page qui n'a pas de ligne `sources` : domaine exclu dans les réglages,
    # jamais lue (D77).
    source_id: str | None
    url: str
    status: Literal["ok", "unreadable"]
    title: str | None
    text: str
    author: str | None
    date: str | None
    lang: str | None
    reason: str | None
    # Source déjà notée dans la session (nœud rejoué, seconde recherche) : son verdict, que
    # `judge` réémet sans rappeler le modèle (D82).
    verdict: SourceVerdictView | None = None


@dataclass(frozen=True)
class PersonFound:
    """Un praticien repéré par l'Éclaireur (SPEC 10.3) : informations professionnelles publiques
    seulement. `url` est une page lue ou un résultat de la session, jamais une adresse écrite par
    le modèle ; `where` : où il publie (domaines)."""

    name: str
    role: str
    url: str
    where: tuple[str, ...]


@dataclass(frozen=True)
class WebLimits:
    languages: tuple[str, ...]
    preferred: tuple[str, ...]
    max_queries: int
    max_pages: int


class WebGateway(Protocol):
    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        categories: Sequence[str] = (),
    ) -> WebSearchResult: ...

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead: ...

    async def judge(
        self,
        user_id: str,
        session_id: str,
        source_id: str,
        *,
        criteria: dict[str, int] | None,
        reason: str,
        summary: str,
    ) -> SourceVerdictView:
        """Note (somme des critères bornés) et verdict d'une source. `criteria=None` : aucune
        note n'a pu être établie, la source est écartée sans note, avec `reason`."""
        ...

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        """Verdicts déjà posés sur ces sources de la session (les autres sont absentes) : un
        `judge` rejoué après un arrêt ne rappelle pas le modèle (D82)."""
        ...

    async def add_person(self, user_id: str, session_id: str, person: PersonFound) -> str:
        """Enregistre le praticien dans les sources de la session (`kind` `person`) ; idempotent
        (même personne, même adresse : même ligne). Rend l'id de la source."""
        ...

    async def people(self, user_id: str, session_id: str) -> list[tuple[str, PersonFound]]:
        """Praticiens déjà enregistrés pour la session, `(source_id, personne)` dans l'ordre
        d'enregistrement : `spot_people` rejoué les réémet sans rappeler le modèle (D84)."""
        ...

    async def limits(self, user_id: str) -> WebLimits: ...


def web_unavailable() -> AppError:
    return AppError("web_unavailable", "La recherche web n'est pas branchée sur ce moteur.", 503)


class _NoWeb:
    """Valeur par défaut du moteur (tests existants, démarrages sans recherche web)."""

    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        categories: Sequence[str] = (),
    ) -> WebSearchResult:
        raise web_unavailable()

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        raise web_unavailable()

    async def judge(
        self,
        user_id: str,
        session_id: str,
        source_id: str,
        *,
        criteria: dict[str, int] | None,
        reason: str,
        summary: str,
    ) -> SourceVerdictView:
        raise web_unavailable()

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        raise web_unavailable()

    async def add_person(self, user_id: str, session_id: str, person: PersonFound) -> str:
        raise web_unavailable()

    async def people(self, user_id: str, session_id: str) -> list[tuple[str, PersonFound]]:
        raise web_unavailable()

    async def limits(self, user_id: str) -> WebLimits:
        raise web_unavailable()


NO_WEB: WebGateway = _NoWeb()
