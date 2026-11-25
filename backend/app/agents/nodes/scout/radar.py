"""The market radar Scout (P5, D159): it searches the month's postings, then reads them in
passes of ten links. No model: the queries are built by the code (`radar_searches`), the links
selected by the code, the pages read by the radar port.

`search`: one search per query (window "month"), links deduplicated by `link_key`, 80 at most,
filed by the port. No possible query or no engine answer: the run fails readably
(`fail("search_unavailable")`), never silently. `read`: rereads `context` at each pass, reads
the next ten unread links (five in parallel) and stops at 50 readable postings, at 60 reads or
with no link left; a node replayed after a stop rereads nothing (the port is idempotent, and
links already read are no longer requested). `finish`: the port's report, stated with the real
numbers (read, blocked, not postings, analyzed). `load` first checks that the Analyst's model
exists: without a key, the run fails right away (`llm_unavailable`), before any search or page
read (D173). If no posting read could be analyzed (the extraction failed), the port returns
`error_code`: the run is `failed` (`analysis_failed`), not "finished" empty.

Logs: identifiers and numbers only, never a link, a site, a job or an area
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
# A query without an answer does not stop the others; the session cap keeps what we have.
_SKIPPED_CODES = frozenset({SEARCH_UNAVAILABLE_CODE, "web_unavailable", "search_query_empty"})

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: MarketRadarState) -> MarketRadarState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


def candidates(found: list[list[str]]) -> list[str]:
    """The links found, one result per query in turn (no query takes all the room), no `link_key`
    duplicates, invalid links discarded, `MAX_CANDIDATES` at most."""
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
    """The Analyst's model must exist before any search or read: otherwise the run fails
    readably right away (`llm_unavailable`), instead of reading 60 pages for nothing."""
    try:
        await deps.models.get_chat_model(deps.user_id, get_agent("analyst").tier, agent="analyst")
    except AppError as exc:
        if exc.code not in MODEL_UNAVAILABLE_CODES:
            raise
        await deps.ports.radar.fail(deps.user_id, deps.session_id, run_id, "llm_unavailable")
        logger.info("No model: session %s, run %s, cause %s", deps.session_id, run_id, exc.code)
        raise AppError("llm_unavailable", NO_MODEL_TEXT, 503) from None


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: MarketRadarState) -> MarketRadarState:
        ctx = await deps.ports.radar.context(deps.user_id, state["run_id"])
        await _require_model(deps, state["run_id"])
        logger.info(
            "Run read: session %s, run %s, %d page(s) already read, %d posting(s) extracted",
            deps.session_id,
            ctx.run_id,
            len(ctx.read),
            len(ctx.extracted),
        )
        return {}

    return load


async def _search_all(deps: GraphDeps, ctx: RadarContext) -> tuple[int, list[list[str]]]:
    """`(queries that answered, links of each)`."""
    answered, found = 0, []
    for search in radar_searches(ctx.role, ctx.zone, ctx.languages):
        try:
            result = await web_search(
                deps, search.query, lang=search.lang, time_range=TIME_RANGE, agent=AGENT
            )
        except AppError as exc:
            if exc.code == QUOTA_CODE:
                break  # session cap: we keep what we have
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
            {"step": "recherche", "intent": "I am searching this month's postings"},
            agent=AGENT,
        )
        answered, found = await _search_all(deps, ctx)
        if answered == 0:
            await deps.ports.radar.fail(deps.user_id, deps.session_id, run_id, "search_unavailable")
            logger.info("Search impossible: session %s, run %s", deps.session_id, run_id)
            raise AppError("search_unavailable", UNAVAILABLE_TEXT, 503)
        urls = candidates(found)
        await deps.ports.radar.save_candidates(
            deps.user_id, deps.session_id, run_id, answered, urls
        )
        logger.info(
            "Search done: session %s, run %s, %d query(ies), %d link(s)",
            deps.session_id,
            run_id,
            answered,
            len(urls),
        )
        return {"urls": urls}

    return search


def unread(urls: list[str], ctx: RadarContext) -> list[str]:
    """The candidate links the run has not read yet, in the search order."""
    done = {link_key(page.url) for page in ctx.read}
    return [url for url in urls if link_key(url) not in done]


def readable(ctx: RadarContext) -> int:
    return sum(page.status == "ok" for page in ctx.read)


def reading_over(ctx: RadarContext, urls: list[str]) -> bool:
    """Nothing left to read: 50 readable postings, 60 reads or no unread link."""
    return readable(ctx) >= MAX_READABLE or ctx.attempts >= MAX_READS or not unread(urls, ctx)


async def _read_all(deps: GraphDeps, run_id: str, batch: list[str]) -> list[PostingPage]:
    """Reads `batch` through the port, `READ_PARALLEL` at a time; if one fails, the others are
    cancelled."""
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
        """One pass: the next ten unread links. `reading_done` is computed on what the port just
        returned, never on a counter kept in the state."""
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
            "Reading: session %s, run %s, %d read(s), %d readable, %d blocked",
            deps.session_id,
            run_id,
            len(after.read),
            readable(after),
            blocked,
        )
        stalled = after.attempts <= before.attempts  # no further read: we do not loop
        return {"reading_done": stalled or reading_over(after, urls)}

    return read


def route_read(state: MarketRadarState) -> str:
    return "extract" if state.get("reading_done") else "read"


def make_finish(deps: GraphDeps) -> Node:
    @node_timeout()
    async def finish(state: MarketRadarState) -> MarketRadarState:
        run_id = state["run_id"]
        report = await deps.ports.radar.finalize(deps.user_id, deps.session_id, run_id)
        if report.error_code is not None:  # no posting analyzed: the run is already `failed`
            logger.info(
                "Run without analysis: session %s, run %s, %d readable, code %s",
                deps.session_id,
                run_id,
                report.read_ok,
                report.error_code,
            )
            raise AppError(report.error_code, NO_ANALYSIS_TEXT, 503)
        artifact = {
            "artifact_id": run_id,
            "kind": "radar",
            "title": "Market Radar",
            "url": f"/career/radar/{run_id}",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        text = summary_text(report)
        _say("bilan", text)
        if (low := sample_text(report)) is not None:
            _say("echantillon", low)
            text = f"{text} {low}"
        logger.info(
            "Run finished: session %s, run %s, %d readable, %d blocked, %d analyzed, "
            "reduced sample %s",
            deps.session_id,
            run_id,
            report.read_ok,
            report.blocked,
            report.analyzed,
            report.low_sample,
        )
        return {"summary": text}

    return finish
