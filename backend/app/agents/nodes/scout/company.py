"""The Scout in `company` mode (SPEC 5.3, D129): the company sheet of a posting, for the CV
review.

Unknown company -> the step is skipped and said in the thread. Sheet less than 30 days old
(`ReviewContext.company_brief`) -> reused as is, without search or write. Otherwise:
`web_search` of the company name, three pages read at most (`page_agent_text`, wrapped),
`CompanyBrief` requested from the model with the posting (wrapped), then filed (`save_company`,
idempotent per company and session). The ATS is recognized from the domain of the posting's
links (application link included) and of the pages read (`detect_ats`). A refused search (cap,
engine absent) or an invalid model output does not block the review: it continues without a
sheet.

Logs: identifiers and numbers, never the company name or an address (17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.scout.models import AGENT
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.ats_hosts import detect_ats
from app.agents.tools.cv_review_port import ReviewContext
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import CompanyBrief
from app.agents.tools.web_port import PageRead
from app.agents.tools.web_tools import page_agent_text, web_read, web_search
from app.core.errors import AppError

COMPANY_REQUEST = "Write the company dossier."
MAX_COMPANY_PAGES = 3
COMPANY_TIMEOUT_S = 300  # one search, three pages (15 s each), one structured output
MAX_POSTING_CHARS = 30_000
UNKNOWN = "The posting does not identify a company. Continuing with the CV review."
NO_BRIEF = "The company dossier could not be prepared. The CV review will continue."

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


async def _pages(deps: GraphDeps, name: str) -> list[PageRead]:
    """The readable pages among the first three results; a search error raises."""
    found = await web_search(deps, name, agent=AGENT)
    pages: list[PageRead] = []
    for hit in found.hits[:MAX_COMPANY_PAGES]:
        try:
            page = await web_read(deps, hit.url, agent=AGENT)
        except AppError:
            continue  # page cap, address refused: the page is skipped
        if page.status == "ok":
            pages.append(page)
    return pages


async def _brief(deps: GraphDeps, name: str, posting: str, pages: list[PageRead]) -> CompanyBrief:
    prompt = render_prompt(
        AGENT,
        mode="company",
        company=untrusted(name, "company"),
        posting=untrusted(posting[:MAX_POSTING_CHARS], "job posting"),
        pages="\n\n".join(page_agent_text(page) for page in pages) or "No pages read.",
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        CompanyBrief,
        [SystemMessage(prompt), HumanMessage(COMPANY_REQUEST)],
        agent=AGENT,
        step="fiche-entreprise",
        intent="Preparing the company dossier",
    )


def _links(ctx: ReviewContext, analysis: PostingAnalysis) -> list[str]:
    return [*ctx.posting_urls, *([analysis.apply_url] if analysis.apply_url else [])]


async def _research(
    deps: GraphDeps, ctx: ReviewContext, name: str, links: list[str]
) -> CvReviewState:
    """Search, sheet requested from the model, sheet filed; nothing filed on failure."""
    try:
        pages = await _pages(deps, name)
        brief = await _brief(deps, name, ctx.posting_text, pages)
    except AppError as exc:
        logger.info("Company sheet abandoned: session %s, code %s", deps.session_id, exc.code)
        _say("fiche", NO_BRIEF)
        return {"company": name, "company_brief": None, "ats": detect_ats(links)}
    sources = [page.url for page in pages]
    ats = detect_ats([*links, *sources])
    await deps.ports.cv_review.save_company(
        deps.user_id, deps.session_id, name, brief, sources, ats
    )
    logger.info(
        "Company sheet filed: session %s, review %s, %d page(s) read, ATS spotted %s",
        deps.session_id,
        ctx.review_id,
        len(pages),
        ats is not None,
    )
    read_count = "1 page read" if len(pages) == 1 else f"{len(pages)} pages read"
    _say("fiche", f"The company dossier is ready ({read_count}).")
    return {"company": name, "company_brief": brief.model_dump(mode="json"), "ats": ats}


def make_company(deps: GraphDeps) -> Node:
    @node_timeout(COMPANY_TIMEOUT_S)
    async def company(state: CvReviewState) -> CvReviewState:
        ctx = await deps.ports.cv_review.context(deps.user_id, state["review_id"])
        analysis = PostingAnalysis.model_validate(state["analysis"])
        links = _links(ctx, analysis)
        name = ctx.company or analysis.company
        if not name:
            logger.info("Unknown company: session %s, review %s", deps.session_id, ctx.review_id)
            _say("fiche", UNKNOWN)
            return {"company": None, "company_brief": None, "ats": detect_ats(links)}
        if ctx.company_brief is not None:
            logger.info(
                "Company sheet reused: session %s, review %s", deps.session_id, ctx.review_id
            )
            _say("fiche", "Using the recent company dossier for this review.")
            brief = ctx.company_brief.model_dump(mode="json")
            return {
                "company": name,
                "company_brief": brief,
                "ats": detect_ats(links) or ctx.company_ats,
            }
        return await _research(deps, ctx, name, links)

    return company
