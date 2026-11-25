"""The Scout's one-page company brief for the application kit (SPEC 6.4, F16, D142).

Reuse and recheck a dossier younger than 30 days without searching or rewriting it.
For a new dossier, search at most twice and read at most four pages, starting with
preferred sources. Number the pages for the model. Verification removes citations
without a read page, clears sections without sources, and drops news older than six
months. If no pages can support a dossier, save a kit piece marked for review.

Logs use identifiers and counts (SPEC 17.2).
"""

import logging
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.scout.models import AGENT, one_line
from app.agents.nodes.tracker.kit_common import Node, Piece, finish, guarded
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.kit_dossier import check_dossier, has_content, render_dossier
from app.agents.tools.kit_schema import CompanyDossier, KitContext, KitStatus, SourceRef
from app.agents.tools.web_port import QUOTA_CODE, SEARCH_UNAVAILABLE_CODE, PageRead, WebHit
from app.agents.tools.web_tools import page_agent_text, web_read, web_search
from app.core.errors import AppError

DOSSIER_REQUEST = "Write the company dossier."
NO_SOURCE = "The dossier needs at least one readable source."
NO_COMPANY = "The company is required to prepare a dossier."
MAX_READS = 4
DOSSIER_LIMIT_S = 360  # Two searches, four page reads, and one structured response.
MAX_POSTING_CHARS = 2000
_URL_ERRORS = ("invalid_url", "url_forbidden")

logger = logging.getLogger(__name__)


async def _hits(deps: GraphDeps, ctx: KitContext) -> list[WebHit]:
    """Search twice and return distinct results with preferred pages first."""
    found: dict[str, WebHit] = {}
    answered = 0
    failure: AppError | None = None
    news = "actualités" if ctx.language == "fr" else "news"
    for query in (ctx.company, f"{ctx.company} {news}"):
        try:
            result = await web_search(deps, query, lang=ctx.language, agent=AGENT)
        except AppError as exc:
            if exc.code == QUOTA_CODE:
                break
            if exc.code == SEARCH_UNAVAILABLE_CODE:
                failure = exc
            elif exc.code != "search_query_empty":
                raise
            continue
        answered += 1
        for hit in result.hits:
            found.setdefault(hit.url, hit)
    if failure is not None and answered == 0:
        raise failure  # Report the provider outage when neither search returned.
    return sorted(found.values(), key=lambda hit: not hit.preferred)  # stable


async def _read(deps: GraphDeps, hits: list[WebHit]) -> list[PageRead]:
    """Read up to four results and keep distinct, readable pages."""
    pages: list[PageRead] = []
    seen: set[str] = set()
    for hit in hits[:MAX_READS]:
        try:
            page = await web_read(deps, hit.url, agent=AGENT)
        except AppError as exc:
            if exc.code == QUOTA_CODE:
                break
            if exc.code not in _URL_ERRORS:
                raise
            continue
        if page.status != "ok" or (page.source_id is not None and page.source_id in seen):
            continue
        if page.source_id is not None:
            seen.add(page.source_id)
        pages.append(page)
    return pages


async def _ask(deps: GraphDeps, ctx: KitContext, pages: list[PageRead]) -> CompanyDossier:
    numbered = [f"[{rank}] {page_agent_text(page)}" for rank, page in enumerate(pages, 1)]
    prompt = render_prompt(
        AGENT,
        mode="dossier",
        company=untrusted(ctx.company, "company"),
        title=untrusted(one_line(ctx.title)[:MAX_POSTING_CHARS], "target role"),
        today=ctx.today.isoformat(),
        pages="\n\n".join(numbered),
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        CompanyDossier,
        [SystemMessage(prompt), HumanMessage(DOSSIER_REQUEST)],
        agent=AGENT,
        step="dossier",
        intent="preparing the company dossier",
    )


def _page_date(page: PageRead) -> date | None:
    """Read the leading ISO date when available."""
    try:
        return date.fromisoformat((page.date or "")[:10])
    except ValueError:
        return None


def _sources(pages: list[PageRead]) -> list[SourceRef]:
    return [
        SourceRef(url=page.url, title=one_line(page.title or "")[:300], source_id=page.source_id)
        for page in pages
    ]


async def _produce(deps: GraphDeps, ctx: KitContext) -> Piece:
    pages = await _read(deps, await _hits(deps, ctx))
    if not pages:
        return Piece("to_check", NO_SOURCE)
    asked = await _ask(deps, ctx, pages)
    dates = [_page_date(page) for page in pages]
    checked = check_dossier(asked, len(pages), ctx.today, page_dates=dates)
    if not has_content(checked.dossier):
        return Piece("to_check", NO_SOURCE)
    sources = _sources(pages)
    await deps.ports.kit.save_dossier(
        deps.user_id, deps.session_id, ctx.company, checked.dossier, sources
    )
    logger.info(
        "Dossier saved: session %s, %d pages read, %d sections cleared, %d items removed",
        deps.session_id,
        len(pages),
        checked.emptied,
        checked.dropped,
    )
    meta = {"sources": len(pages), "emptied": checked.emptied, "dropped": checked.dropped}
    status: KitStatus = "to_check" if checked.emptied else "ready"
    return Piece(status, render_dossier(ctx.company, checked.dossier, sources), meta)


def _reused(ctx: KitContext, dossier: CompanyDossier) -> Piece:
    """Recheck the saved dossier for missing sections and outdated news."""
    sources = ctx.company_dossier_sources
    checked = check_dossier(dossier, len(sources), ctx.today)
    meta = {
        "sources": len(sources),
        "reused": True,
        "emptied": checked.emptied,
        "dropped": checked.dropped,
    }
    status: KitStatus = "to_check" if checked.emptied else "ready"
    return Piece(status, render_dossier(ctx.company, checked.dossier, sources), meta)


def make_dossier(deps: GraphDeps) -> Node:
    async def company_brief(state: ApplicationKitState) -> ApplicationKitState:
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])
        if not ctx.company.strip():
            done = Piece("to_check", NO_COMPANY)
        elif ctx.company_dossier is not None:
            logger.info(
                "Dossier reused: session %s, application %s", deps.session_id, ctx.application_id
            )
            done = _reused(ctx, ctx.company_dossier)
        else:
            done = await guarded(DOSSIER_LIMIT_S, lambda: _produce(deps, ctx))
        return await finish(deps, ctx.application_id, "company_brief", done, agent=AGENT)

    return node_timeout(DOSSIER_LIMIT_S + 60)(company_brief)
