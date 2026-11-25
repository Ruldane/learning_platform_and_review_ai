"""The Scout of the daily brief (P11, D161): the morning resource. The code searches the day's
topic on the web (window "month"), the Scout picks a result among the first eight
(`ResourcePick`, one call), then **the code reads the chosen page**: an unreadable page is never
filed, the following results are read in order (three reads at most, without a new model call).
No readable page, no topic, no result, a search or a model that is down: the section stays empty
(`None`), never invented, and the flow continues to the advice.

The filed address is that of a search result (never an address written by the model), and only
the `why` sentence comes from the model. The results come from the web: wrapped by `untrusted`
(17.4).

Logs: identifiers, numbers and codes only, never a topic, a link, a title or a text
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
TIME_RANGE = "month"  # search window: what is recent
BUDGET_S = 90.0  # shorter than the node cap: a timeout empties the section, not the brief
SNIPPET_MAX = 300
TITLE_MAX = 200
DATE_MAX = 40
LANGUAGES = {"fr": "French", "en": "English"}
# `why` of a result the model did not choose (its own was unreadable): said by the code, so as
# not to attribute to the model a reason it gave to another result.
FALLBACK_WHY = {
    "fr": "Un autre résultat de la recherche du mois sur ce sujet.",
    "en": "Another result of this month's search on this topic.",
}

logger = logging.getLogger(__name__)


def usable_hits(hits: list[WebHit]) -> list[WebHit]:
    """The results shown: valid http(s) link, no duplicates (`link_key`), `RESULTS` at most,
    in the search order."""
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
    """The ranks (from 0) read in order: the model's choice first, then the other results in
    the search order; `READS` at most."""
    return ([picked] + [rank for rank in range(count) if rank != picked])[:READS]


def why_of(pick: ResourcePick, hit: WebHit, language: Literal["fr", "en"]) -> str:
    """The model's reason, if each of its numbers appears in what the result shows (title,
    excerpt, date, address): a model does not attribute to a page "10 years of experience" or "5
    hours" that nothing states. Otherwise, the code's sentence."""
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
    """`(read, page date, cap reached)`. A refused page or one in error, even raw (a reader
    failure), is not read: the fallback moves to the next result."""
    try:
        page = await web_read(deps, hit.url, agent=AGENT)
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        logger.info("Brief page not read: session %s, cause %s", deps.session_id, code)
        return False, None, code == QUOTA_CODE
    return page.status == "ok" and bool(page.text.strip()), page.date, False


async def read_resource(
    deps: GraphDeps, hits: list[WebHit], pick: ResourcePick, language: Literal["fr", "en"]
) -> ResourceView | None:
    """The first readable page, the model's choice first; `None` if none of the first `READS`
    can be read, or if the model chose nothing (null `index`, or a rank absent from the list:
    never a result it did not designate, picked at random)."""
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
    """The day's resource, or `None`: without a topic, a result, a choice or a page read."""
    topic = (ctx.topic or "").strip()
    if not topic:
        return None
    # The model first: without a key, the web search (a quota, a rate) is not spent.
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
        """The "resource" section: skipped if already filed (node replayed). Whatever happens to
        the search, the reading or the model, the section is emptied and the flow continues:
        the advice does not depend on it."""
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
        except Exception as exc:  # a section that is down does not stop the other
            code = exc.code if isinstance(exc, AppError) else type(exc).__name__
            logger.info("Brief resource empty: session %s, cause %s", deps.session_id, code)
        await deps.ports.brief.save_resource(deps.user_id, deps.session_id, brief_id, view)
        logger.info(
            "Brief resource stored: session %s, brief %s, found %s",
            deps.session_id,
            brief_id,
            view is not None,
        )
        return {}

    return resource
