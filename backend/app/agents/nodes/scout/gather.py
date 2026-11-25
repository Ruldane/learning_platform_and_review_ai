"""Scout nodes that collect: prepare the queries, search, read. Each node is a function of
`GraphDeps`; each external call is idempotent through the gateway (trap 9.4): a replayed node
neither recounts a query or a page nor duplicates any source."""

from typing import Any
from urllib.parse import urlsplit

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.scout.models import (
    AGENT,
    MAX_PAGES_PER_RUN,
    MAX_QUERIES_TOTAL,
    PAGE_CHARS_FOR_SCORING,
    QUERIES_PER_LANGUAGE,
    Node,
    PlannedQuery,
    SearchPlan,
    one_line,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.web_research import WebResearchState
from app.agents.tools.web_port import QUOTA_CODE, SEARCH_UNAVAILABLE_CODE, PageRead
from app.agents.tools.web_tools import web_read, web_search
from app.core.errors import AppError

READ_TIMEOUT_S = 300  # up to 15 s per page, one query per second and per domain
SEARCH_TIMEOUT_S = 180
# Address errors: the page is reported unreadable (fixed message), the search continues.
_URL_ERRORS = ("invalid_url", "url_forbidden")


def _fit(plan: SearchPlan, languages: tuple[str, ...], limit: int) -> list[PlannedQuery]:
    """Queries in the configured languages, without duplicates, truncated to the session cap."""
    seen: set[tuple[str, str]] = set()
    kept: list[PlannedQuery] = []
    for query in plan.queries:
        key = (one_line(query.text).lower(), query.lang)
        if query.lang in languages and key not in seen:
            seen.add(key)
            kept.append(query)
    return kept[:limit]


def make_plan(deps: GraphDeps) -> Node:
    @node_timeout()
    async def plan(state: WebResearchState) -> WebResearchState:
        limits = await deps.web.limits(deps.user_id)
        languages = limits.languages or ("fr",)
        prompt = render_prompt(
            AGENT,
            mode="plan",
            query=state["query"],
            languages=", ".join(languages),
            per_language=QUERIES_PER_LANGUAGE,
            max_queries=min(MAX_QUERIES_TOTAL, QUERIES_PER_LANGUAGE * len(languages)),
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        found = await structured_call(
            model,
            SearchPlan,
            [SystemMessage(prompt), HumanMessage("Prepare the search queries.")],
            agent=AGENT,
            step="plan",
            intent="preparing the search queries",
        )
        queries = _fit(found, languages, max(1, limits.max_queries))
        if not queries:  # the model returned nothing usable: the request itself
            queries = [PlannedQuery(text=one_line(state["query"])[:200], lang=languages[0])]
        return {"queries": [query.model_dump() for query in queries]}

    return plan


def make_search(deps: GraphDeps) -> Node:
    @node_timeout(SEARCH_TIMEOUT_S)
    async def search(state: WebResearchState) -> WebResearchState:
        hits: dict[str, dict[str, Any]] = {}
        answered = 0
        failure: AppError | None = None
        for query in state.get("queries", []):
            try:
                found = await web_search(deps, query["text"], lang=query["lang"], agent=AGENT)
            except AppError as exc:
                if exc.code == QUOTA_CODE:
                    break  # session cap: we keep what we have
                if exc.code == SEARCH_UNAVAILABLE_CODE:
                    failure = exc
                    continue
                if exc.code == "search_query_empty":
                    continue  # query reduced to nothing once cleaned
                raise
            answered += 1
            for hit in found.hits:
                hits.setdefault(
                    hit.url, {"url": hit.url, "title": hit.title, "preferred": hit.preferred}
                )
        if failure is not None and answered == 0:
            raise failure  # engine down: the session fails with its readable message
        ordered = sorted(hits.values(), key=lambda hit: not hit["preferred"])  # stable
        return {"hits": ordered}

    return search


def _is_preferred(url: str, preferred: tuple[str, ...]) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith(f".{d}") for d in (p.lower() for p in preferred))


def _to_read(state: WebResearchState, budget: int) -> list[str]:
    """Addresses to read: results (preferred first) then the input's addresses, no duplicates.
    The input's addresses are read in priority over the results when the cap is low."""
    extra = list(dict.fromkeys(state.get("urls", [])))[:budget]
    room = max(0, budget - len(extra))
    found = [hit["url"] for hit in state.get("hits", [])][: min(room, MAX_PAGES_PER_RUN)]
    return list(dict.fromkeys(found + extra))


def _unreadable(url: str, reason: str, page: PageRead | None = None) -> None:
    """Page not read: reported right away, never scored or cited."""
    emit(
        "source.found",
        {
            "title": one_line(page.title or "") if page and page.title else url,
            "url": page.url if page else url,
            "author": None,
            "date": None,
            "lang": None,
            "score": None,
            "source_id": page.source_id if page else None,
            "status": "unreadable",
            "verdict": None,
            "reason": reason,
        },
        agent=AGENT,
    )


def make_read(deps: GraphDeps) -> Node:
    @node_timeout(READ_TIMEOUT_S)
    async def read(state: WebResearchState) -> WebResearchState:
        limits = await deps.web.limits(deps.user_id)
        extra = len(state.get("urls", []))
        budget = max(0, min(MAX_PAGES_PER_RUN + extra, limits.max_pages))
        pages: list[dict[str, Any]] = []
        seen: set[str] = set()
        unreadable = 0
        for url in _to_read(state, budget):
            try:
                page = await web_read(deps, url, agent=AGENT)
            except AppError as exc:
                if exc.code == QUOTA_CODE:
                    break
                if exc.code not in _URL_ERRORS:
                    raise
                _unreadable(url, exc.message)
                unreadable += 1
                continue
            if page.source_id is not None:
                if page.source_id in seen:
                    continue  # same page through two addresses
                seen.add(page.source_id)
            if page.status != "ok":
                reason = page.reason or "Page illisible."
                _unreadable(url, reason, page)
                unreadable += 1
                if page.source_id is not None and page.verdict is None:  # no longer "pending"
                    await deps.web.judge(
                        deps.user_id, deps.session_id, page.source_id, criteria={}, reason=reason,
                        summary="",
                    )  # fmt: skip
                continue
            pages.append(_scoring_page(page, limits.preferred))
        return {"pages": pages, "unreadable": unreadable}

    return read


def _scoring_page(page: PageRead, preferred: tuple[str, ...]) -> dict[str, Any]:
    return {
        "source_id": page.source_id,
        "url": page.url,
        "title": page.title,
        "author": page.author,
        "date": page.date,
        "lang": page.lang,
        "text": page.text[:PAGE_CHARS_FOR_SCORING],
        "preferred": _is_preferred(page.url, preferred),
        "verdict": _known_verdict(page),
    }


def _known_verdict(page: PageRead) -> dict[str, Any] | None:
    """Verdict already set in the session (D82), kept in the state so that `judge` does not call
    the model again."""
    known = page.verdict
    if known is None:
        return None
    return {
        "score": known.score,
        "verdict": known.verdict,
        "reason": known.reason,
        "summary": known.summary,
    }
