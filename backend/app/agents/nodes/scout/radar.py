"""L'Éclaireur du radar du marché (P5, D159) : il cherche les offres du mois, puis les lit par
passages de dix liens. Aucun modèle : les requêtes sont construites par le code (`radar_searches`),
les liens retenus par le code, les pages lues par le port du radar.

`search` : une recherche par requête (fenêtre « month »), liens dédoublonnés par `link_key`, 80 au
plus, rangés par le port. Aucune requête possible ou aucune réponse du moteur : le relevé échoue
lisiblement (`fail("search_unavailable")`), jamais en silence. `read` : relit `context` à chaque
passage, lit les dix prochains liens non lus (cinq en parallèle) et s'arrête à 50 offres lisibles,
à 60 lectures ou sans lien restant ; un nœud rejoué après un arrêt ne relit rien (le port est
idempotent, et les liens déjà lus ne sont plus demandés). `finish` : le rapport du port, dit avec
les nombres réels (lues, bloquées, pas des offres, analysées). `load` vérifie d'abord que le modèle
de l'Analyste existe : sans clé, le relevé échoue tout de suite (`llm_unavailable`), avant la
moindre recherche ou lecture de page (D173). Si aucune offre lue n'a pu être analysée (l'extraction
a échoué), le port rend `error_code` : le relevé est `failed` (`analysis_failed`), pas « terminé » à
vide.

Journaux : identifiants et nombres seulement, jamais un lien, un site, un poste ni une zone
(17.2)."""

import asyncio
import logging
from itertools import zip_longest
from typing import Protocol

from app.agents.nodes.scout.radar_text import (
    NO_ANALYSIS_TEXT,
    NO_MODEL_TEXT,
    UNAVAILABLE_TEXT,
    counting_text,
    sample_text,
    summary_text,
)
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.market_radar import MarketRadarState
from app.agents.tools.brief_port import MODEL_UNAVAILABLE_CODES
from app.agents.tools.radar_port import (
    MAX_CANDIDATES,
    MAX_READABLE,
    MAX_READS,
    PostingPage,
    RadarContext,
)
from app.agents.tools.radar_schema import (
    READ_BATCH,
    READ_PARALLEL,
    TIME_RANGE,
    link_key,
    radar_searches,
)
from app.agents.tools.web_port import QUOTA_CODE, SEARCH_UNAVAILABLE_CODE
from app.agents.tools.web_tools import web_search
from app.core.errors import AppError

AGENT = "scout"
# Une requête sans réponse n'arrête pas les autres ; le plafond de la session garde ce qu'on a.
_SKIPPED_CODES = frozenset({SEARCH_UNAVAILABLE_CODE, "web_unavailable", "search_query_empty"})

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: MarketRadarState) -> MarketRadarState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


def candidates(found: list[list[str]]) -> list[str]:
    """Les liens trouvés, un résultat par requête à tour de rôle (aucune requête ne prend toute la
    place), sans doublon de `link_key`, liens invalides écartés, `MAX_CANDIDATES` au plus."""
    seen: set[str] = set()
    urls: list[str] = []
    for round_ in zip_longest(*found):
        for url in round_:
            key = link_key(url) if url else None
            if key is not None and key not in seen and len(urls) < MAX_CANDIDATES:
                seen.add(key)
                urls.append(url)
    return urls


async def _require_model(deps: GraphDeps, run_id: str) -> None:
    """Le modèle de l'Analyste doit exister avant toute recherche ou lecture : sinon le relevé
    échoue lisiblement tout de suite (`llm_unavailable`), au lieu de lire 60 pages pour rien."""
    try:
        await deps.models.get_chat_model(deps.user_id, get_agent("analyst").tier, agent="analyst")
    except AppError as exc:
        if exc.code not in MODEL_UNAVAILABLE_CODES:
            raise
        await deps.ports.radar.fail(deps.user_id, deps.session_id, run_id, "llm_unavailable")
        logger.info(
            "Aucun modèle : session %s, relevé %s, cause %s", deps.session_id, run_id, exc.code
        )
        raise AppError("llm_unavailable", NO_MODEL_TEXT, 503) from None


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: MarketRadarState) -> MarketRadarState:
        ctx = await deps.ports.radar.context(deps.user_id, state["run_id"])
        await _require_model(deps, state["run_id"])
        logger.info(
            "Relevé lu : session %s, relevé %s, %d page(s) déjà lue(s), %d offre(s) extraite(s)",
            deps.session_id,
            ctx.run_id,
            len(ctx.read),
            len(ctx.extracted),
        )
        return {}

    return load


async def _search_all(deps: GraphDeps, ctx: RadarContext) -> tuple[int, list[list[str]]]:
    """`(requêtes qui ont répondu, liens de chacune)`."""
    answered, found = 0, []
    for search in radar_searches(ctx.role, ctx.zone, ctx.languages):
        try:
            result = await web_search(
                deps, search.query, lang=search.lang, time_range=TIME_RANGE, agent=AGENT
            )
        except AppError as exc:
            if exc.code == QUOTA_CODE:
                break  # plafond de la session : on garde ce qu'on a
            if exc.code in _SKIPPED_CODES:
                continue
            raise
        answered += 1
        found.append([hit.url for hit in result.hits])
    return answered, found


def make_search(deps: GraphDeps) -> Node:
    @node_timeout()
    async def search(state: MarketRadarState) -> MarketRadarState:
        run_id = state["run_id"]
        ctx = await deps.ports.radar.context(deps.user_id, run_id)
        emit(
            "agent.started",
            {"step": "recherche", "intent": "je cherche les offres du mois"},
            agent=AGENT,
        )
        answered, found = await _search_all(deps, ctx)
        if answered == 0:
            await deps.ports.radar.fail(deps.user_id, deps.session_id, run_id, "search_unavailable")
            logger.info("Recherche impossible : session %s, relevé %s", deps.session_id, run_id)
            raise AppError("search_unavailable", UNAVAILABLE_TEXT, 503)
        urls = candidates(found)
        await deps.ports.radar.save_candidates(
            deps.user_id, deps.session_id, run_id, answered, urls
        )
        logger.info(
            "Recherche faite : session %s, relevé %s, %d requête(s), %d lien(s)",
            deps.session_id,
            run_id,
            answered,
            len(urls),
        )
        return {"urls": urls}

    return search


def unread(urls: list[str], ctx: RadarContext) -> list[str]:
    """Les liens candidats que le relevé n'a pas encore lus, dans l'ordre de la recherche."""
    done = {link_key(page.url) for page in ctx.read}
    return [url for url in urls if link_key(url) not in done]


def readable(ctx: RadarContext) -> int:
    return sum(page.status == "ok" for page in ctx.read)


def reading_over(ctx: RadarContext, urls: list[str]) -> bool:
    """Plus rien à lire : 50 offres lisibles, 60 lectures ou plus de lien non lu."""
    return readable(ctx) >= MAX_READABLE or ctx.attempts >= MAX_READS or not unread(urls, ctx)


async def _read_all(deps: GraphDeps, run_id: str, batch: list[str]) -> list[PostingPage]:
    """Lit `batch` par le port, `READ_PARALLEL` à la fois ; si l'une échoue, les autres sont
    annulées."""
    gate = asyncio.Semaphore(READ_PARALLEL)

    async def one(url: str) -> PostingPage:
        async with gate:
            return await deps.ports.radar.read_posting(deps.user_id, deps.session_id, run_id, url)

    tasks = [asyncio.ensure_future(one(url)) for url in batch]
    try:
        return list(await asyncio.gather(*tasks))
    except BaseException:
        for task in tasks:
            task.cancel()
        raise


def make_read(deps: GraphDeps) -> Node:
    @node_timeout()
    async def read(state: MarketRadarState) -> MarketRadarState:
        """Un passage : les dix prochains liens non lus. `reading_done` est calculé sur ce que le
        port vient de rendre, jamais sur un compteur gardé dans l'état."""
        run_id, urls = state["run_id"], state.get("urls", [])
        before = await deps.ports.radar.context(deps.user_id, run_id)
        if reading_over(before, urls):
            return {"reading_done": True}
        batch = unread(urls, before)[: min(READ_BATCH, MAX_READS - before.attempts)]
        await _read_all(deps, run_id, batch)
        after = await deps.ports.radar.context(deps.user_id, run_id)
        blocked = len(after.read) - readable(after)
        _say(f"lecture-{len(after.read)}", counting_text(readable(after), blocked))
        logger.info(
            "Lecture : session %s, relevé %s, %d lecture(s), %d lisible(s), %d bloquée(s)",
            deps.session_id,
            run_id,
            len(after.read),
            readable(after),
            blocked,
        )
        stalled = after.attempts <= before.attempts  # aucune lecture de plus : on ne boucle pas
        return {"reading_done": stalled or reading_over(after, urls)}

    return read


def route_read(state: MarketRadarState) -> str:
    return "extract" if state.get("reading_done") else "read"


def make_finish(deps: GraphDeps) -> Node:
    @node_timeout()
    async def finish(state: MarketRadarState) -> MarketRadarState:
        run_id = state["run_id"]
        report = await deps.ports.radar.finalize(deps.user_id, deps.session_id, run_id)
        if report.error_code is not None:  # aucune offre analysée : le relevé est déjà `failed`
            logger.info(
                "Relevé sans analyse : session %s, relevé %s, %d lisible(s), code %s",
                deps.session_id,
                run_id,
                report.read_ok,
                report.error_code,
            )
            raise AppError(report.error_code, NO_ANALYSIS_TEXT, 503)
        artifact = {
            "artifact_id": run_id,
            "kind": "radar",
            "title": "Radar du marché",
            "url": f"/career/radar/{run_id}",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        text = summary_text(report)
        _say("bilan", text)
        if (low := sample_text(report)) is not None:
            _say("echantillon", low)
            text = f"{text} {low}"
        logger.info(
            "Relevé fini : session %s, relevé %s, %d lisible(s), %d bloquée(s), %d analysée(s), "
            "échantillon réduit %s",
            deps.session_id,
            run_id,
            report.read_ok,
            report.blocked,
            report.analyzed,
            report.low_sample,
        )
        return {"summary": text}

    return finish
