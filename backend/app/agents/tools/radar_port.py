"""Port du radar du marché (P5, P6, D159). `app.agents` n'importe aucune feature (contrat 6) : il
décrit ici ce dont le parcours `market_radar` a besoin ; la feature `radar` l'implémente
(`AgentRadarStore`, tâche 8.4).

Les liens, les pages et les extractions sont des données de l'utilisatrice ou du web (17.2, 17.4) :
jamais journalisés, ni ici ni par l'implémentation. Toute écriture est **idempotente** (SPEC 9.4) :
un nœud rejoué après un arrêt n'écrit, ne relit et ne recompte rien de plus.

- `context` : lecture seule ; l'état du relevé tel qu'il est en base (pages lues, offres extraites,
  lectures faites). La boucle de lecture et celle d'extraction le relisent à chaque passage.
- `read_posting` : lit la page (lecteur web du moteur, hors plafond de pages de session : budget
  propre de `MAX_READS`) et la range ; idempotent par (relevé, lien normalisé par
  `posting_url_key`) : une page déjà lue est rendue sans relecture ni recompte. Une page qui ne se
  lit pas (site bloqué, lien refusé) n'est pas une erreur : `status = "unreadable"`.
- `save_extraction` : les offres extraites (`RadarFinding`), `ref` = `PostingPage.ref` ;
  `failed_refs` : les pages
  dont l'extraction a échoué (comptées comme extraites pour ne pas être reprises). Idempotent par
  `ref`.
- `finalize` : calcule le rapport (nombres réels : lues, bloquées, pas des offres, analysées).
- `fail` : le relevé échoue avec ce code (`search_unavailable`…), sans rien d'autre."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.tools.radar_schema import RadarFinding
from app.core.errors import AppError

# Bornes de P5, recopiées de `radar.service.rules` (le moteur n'importe pas la feature) : un test
# vérifie qu'elles sont les mêmes.
MAX_CANDIDATES = 80  # liens gardés après la recherche
MAX_READS = 60  # lectures au plus par relevé
MAX_READABLE = 50  # arrêt de la lecture à 50 offres lisibles, et aucune extraction au-delà


@dataclass(frozen=True)
class PostingPage:
    """Une page lue. `ref` : son repère stable dans le relevé ; `url` : le lien tel que donné à
    `read_posting` ; `domain` : son site (compté à part quand il bloque) ; `text` : vide si
    `unreadable`."""

    ref: str
    url: str
    domain: str
    status: Literal["ok", "unreadable"]
    text: str


@dataclass(frozen=True)
class RadarContext:
    run_id: str
    role: str
    zone: str
    languages: tuple[str, ...]
    read: list[PostingPage] = field(
        default_factory=list
    )  # pages déjà lues, dans l'ordre de lecture
    extracted: frozenset[str] = frozenset()  # refs déjà extraites (ou en échec d'extraction)
    attempts: int = 0  # lectures déjà faites (≤ MAX_READS)


@dataclass(frozen=True)
class RadarSummary:
    """Le rapport du relevé : `read_ok` pages lisibles (dont `not_postings` qui ne sont pas des
    offres), `blocked` pages illisibles, `analyzed` offres analysées, `low_sample` : moins de 30
    offres lisibles."""

    read_ok: int
    blocked: int
    not_postings: int
    analyzed: int
    low_sample: bool


class RadarStore(Protocol):
    async def context(self, user_id: str, run_id: str) -> RadarContext: ...

    async def save_candidates(
        self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]
    ) -> None: ...

    async def read_posting(
        self, user_id: str, session_id: str, run_id: str, url: str
    ) -> PostingPage: ...

    async def save_extraction(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        items: list[RadarFinding],
        failed_refs: list[str],
    ) -> None: ...

    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary: ...

    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None: ...


def radar_unavailable() -> AppError:
    return AppError("radar_unavailable", "Le radar du marché n'est pas branché sur ce moteur.", 503)


class _NoRadar:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def context(self, user_id: str, run_id: str) -> RadarContext:
        raise radar_unavailable()

    async def save_candidates(
        self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]
    ) -> None:
        raise radar_unavailable()

    async def read_posting(
        self, user_id: str, session_id: str, run_id: str, url: str
    ) -> PostingPage:
        raise radar_unavailable()

    async def save_extraction(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        items: list[RadarFinding],
        failed_refs: list[str],
    ) -> None:
        raise radar_unavailable()

    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary:
        raise radar_unavailable()

    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None:
        raise radar_unavailable()


NO_RADAR: RadarStore = _NoRadar()
