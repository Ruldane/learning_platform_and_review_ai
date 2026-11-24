"""L'Éclaireur du brief du jour (P11, D161) : la ressource du matin. Le code cherche le sujet du
jour sur le web (fenêtre « month »), l'Éclaireur choisit un résultat parmi les huit premiers
(`ResourcePick`, un appel), puis **le code lit la page choisie** : une page illisible n'est jamais
rangée, les résultats suivants sont lus dans l'ordre (trois lectures au plus, sans nouvel appel au
modèle). Aucune page lisible, aucun sujet, aucun résultat, une recherche ou un modèle en panne :
la rubrique reste vide (`None`), jamais inventée, et le parcours continue vers le conseil.

L'adresse rangée est celle d'un résultat de la recherche (jamais une adresse écrite par le modèle),
et seule la phrase `why` vient du modèle. Les résultats viennent du web : encadrés par `untrusted`
(17.4).

Journaux : identifiants, nombres et codes seulement, jamais un sujet, un lien, un titre ni un texte
(17.2)."""

import asyncio
import logging
from typing import Literal
from urllib.parse import urlsplit

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.errors import GraphInterrupt

from app.agents.nodes.scout.models import one_line
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.daily_brief import DailyBriefState, Node
from app.agents.tools.brief_port import BriefContext
from app.agents.tools.brief_schema import READS, RESULTS, ResourcePick, ResourceView
from app.agents.tools.cv_lexicon import figures_in
from app.agents.tools.radar_schema import link_key
from app.agents.tools.web_port import QUOTA_CODE, WebHit
from app.agents.tools.web_tools import web_read, web_search
from app.core.errors import AppError

AGENT = "scout"
TIME_RANGE = "month"  # fenêtre de la recherche : ce qui est récent
BUDGET_S = 90.0  # plus court que le plafond du nœud : un dépassement vide la rubrique, pas le brief
SNIPPET_MAX = 300
TITLE_MAX = 200
DATE_MAX = 40
LANGUAGES = {"fr": "French", "en": "English"}
# `why` d'un résultat que le modèle n'a pas choisi (le sien était illisible) : dit par le code, pour
# ne pas prêter au modèle une raison qu'il a donnée à un autre résultat.
FALLBACK_WHY = {
    "fr": "Un autre résultat de la recherche du mois sur ce sujet.",
    "en": "Another result of this month's search on this topic.",
}

logger = logging.getLogger(__name__)


def usable_hits(hits: list[WebHit]) -> list[WebHit]:
    """Les résultats montrés : lien http(s) valide, sans doublon (`link_key`), `RESULTS` au plus,
    dans l'ordre de la recherche."""
    seen: set[str] = set()
    kept: list[WebHit] = []
    for hit in hits:
        key = link_key(hit.url)
        if key is not None and key not in seen:
            seen.add(key)
            kept.append(hit)
    return kept[:RESULTS]


def domain_of(url: str) -> str:
    return (urlsplit(url).hostname or "").removeprefix("www.")


def results_text(hits: list[WebHit]) -> str:
    """Number the search results and wrap them as untrusted data."""
    lines = []
    for number, hit in enumerate(hits, 1):
        date = hit.published or "date unknown"
        head = f"{number}. {one_line(hit.title)} ({domain_of(hit.url)}, {date})"
        lines.append(f"{head}\n{one_line(hit.snippet)[:SNIPPET_MAX]}")
    return untrusted("\n\n".join(lines), "search results")


async def _choose(
    deps: GraphDeps, model: BaseChatModel, ctx: BriefContext, topic: str, hits: list[WebHit]
) -> ResourcePick:
    prompt = render_prompt(
        AGENT,
        mode="brief_resource",
        topic=untrusted(one_line(topic), "topic of the day"),
        count=len(hits),
        results=results_text(hits),
        language=LANGUAGES[ctx.language],
    )
    return await structured_call(
        model,
        ResourcePick,
        [SystemMessage(prompt), HumanMessage("Choose today's resource.")],
        agent=AGENT,
        step="ressource",
        intent="choosing today's resource",
    )


def read_order(count: int, picked: int) -> list[int]:
    """Les rangs (à partir de 0) lus dans l'ordre : le choix du modèle d'abord, puis les autres
    résultats dans l'ordre de la recherche ; `READS` au plus."""
    return ([picked] + [rank for rank in range(count) if rank != picked])[:READS]


def why_of(pick: ResourcePick, hit: WebHit, language: Literal["fr", "en"]) -> str:
    """La raison du modèle, si chacun de ses nombres figure dans ce que le résultat montre (titre,
    extrait, date, adresse) : un modèle ne prête pas à une page « 10 ans d'expérience » ou « 5
    heures » que rien ne dit. Sinon, la phrase du code."""
    why = one_line(pick.why)
    shown = figures_in(" ".join([hit.title, hit.snippet, hit.published or "", hit.url]))
    return why if figures_in(why) <= shown else FALLBACK_WHY[language]


def _view(hit: WebHit, why: str, page_date: str | None) -> ResourceView:
    published = hit.published or page_date
    return ResourceView(
        title=one_line(hit.title)[:TITLE_MAX],
        url=hit.url,
        domain=domain_of(hit.url),
        published=published[:DATE_MAX] if published else None,
        why=why,
    )


async def _read_one(deps: GraphDeps, hit: WebHit) -> tuple[bool, str | None, bool]:
    """`(lue, date de la page, plafond atteint)`. Une page refusée ou en erreur, même brute (une
    panne du lecteur), n'est pas lue : le repli passe au résultat suivant."""
    try:
        page = await web_read(deps, hit.url, agent=AGENT)
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        logger.info("Page du brief non lue : session %s, cause %s", deps.session_id, code)
        return False, None, code == QUOTA_CODE
    return page.status == "ok" and bool(page.text.strip()), page.date, False


async def read_resource(
    deps: GraphDeps, hits: list[WebHit], pick: ResourcePick, language: Literal["fr", "en"]
) -> ResourceView | None:
    """La première page lisible, le choix du modèle d'abord ; `None` si aucune des `READS`
    premières ne se lit, ou si le modèle n'a rien choisi (`index` nul, ou un rang absent de la
    liste : jamais un résultat qu'il n'a pas désigné au hasard)."""
    if pick.index is None or pick.index > len(hits):
        return None
    picked = pick.index - 1
    for rank in read_order(len(hits), picked):
        readable, page_date, quota = await _read_one(deps, hits[rank])
        if readable:
            why = why_of(pick, hits[rank], language) if rank == picked else FALLBACK_WHY[language]
            return _view(hits[rank], why, page_date)
        if quota:
            break
    return None


async def find_resource(deps: GraphDeps, ctx: BriefContext) -> ResourceView | None:
    """La ressource du jour, ou `None` : sans sujet, sans résultat, sans choix ou sans page lue."""
    topic = (ctx.topic or "").strip()
    if not topic:
        return None
    # Le modèle d'abord : sans clé, la recherche web (un quota, un débit) n'est pas dépensée.
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    found = await web_search(deps, topic, time_range=TIME_RANGE, agent=AGENT)
    hits = usable_hits(found.hits)
    if not hits:
        return None
    pick = await _choose(deps, model, ctx, topic, hits)
    return await read_resource(deps, hits, pick, ctx.language)


def make_resource(deps: GraphDeps) -> Node:
    @node_timeout()
    async def resource(state: DailyBriefState) -> DailyBriefState:
        """La rubrique « ressource » : sautée si elle est déjà rangée (nœud rejoué). Quoi qu'il
        arrive à la recherche, à la lecture ou au modèle, la rubrique se vide et le parcours
        continue : le conseil ne dépend pas d'elle."""
        brief_id = state["brief_id"]
        ctx = await deps.ports.brief.context(deps.user_id, brief_id)
        if ctx.resource_done:
            return {}
        view: ResourceView | None = None
        try:
            async with asyncio.timeout(BUDGET_S):
                view = await find_resource(deps, ctx)
        except GraphInterrupt:
            raise
        except Exception as exc:  # une rubrique en panne n'arrête pas l'autre
            code = exc.code if isinstance(exc, AppError) else type(exc).__name__
            logger.info("Ressource du brief vide : session %s, cause %s", deps.session_id, code)
        await deps.ports.brief.save_resource(deps.user_id, deps.session_id, brief_id, view)
        logger.info(
            "Ressource du brief rangée : session %s, brief %s, trouvée %s",
            deps.session_id,
            brief_id,
            view is not None,
        )
        return {}

    return resource
