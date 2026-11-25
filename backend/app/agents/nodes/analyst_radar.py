"""The market radar Analyst (P6, D159): it reads postings in batches of five (4,000 characters
each, wrapped as untrusted) and extracts skills, tools, level and salary. The code checks what it
returns before storing it: an unknown reference is ignored, a tool absent from the text is
removed, a salary whose figures are not in the text is removed. A batch that the model cannot
make valid (after the retries of `structured_call`) marks its pages as extraction failures and the
loop continues; another provider failure (timeout, limit) on a batch marks it the same way without
losing the batches already stored, and the extraction stops after `MAX_FAILED_BATCHES` failed
batches (the rest is reported as "read, not analyzed", D173). A page missing from the answer is
treated the same way: never a page left without an outcome, never an endless loop.

The loop rereads the port's `context` at each pass: an extraction already stored is never redone
after a restart (SPEC 9.4). At most `MAX_READABLE` pages are extracted (10 calls).

Logs: identifiers and numbers only, never a link, a site, a posting text, a job or an area
(17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.market_radar import MarketRadarState
from app.agents.tools.brief_port import MODEL_UNAVAILABLE_CODES
from app.agents.tools.posting_schema import contains_term, normalize_term
from app.agents.tools.radar_port import MAX_READABLE, PostingPage
from app.agents.tools.radar_schema import (
    BATCH,
    TEXT_MAX,
    RadarBatch,
    RadarFinding,
    RadarItem,
    salary_in_text,
)
from app.core.errors import AppError

AGENT = "analyst"
RADAR_REQUEST = "Extract these postings from the market snapshot."
INVALID_CODE = "structured_output_invalid"
MAX_FAILED_BATCHES = 2  # provider-failed batches after which the extraction stops

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: MarketRadarState) -> MarketRadarState: ...


def local_ref(position: int) -> str:
    """A posting's marker in the batch: `p1` to `p5`."""
    return f"p{position}"


def radar_vars(batch: list[PostingPage]) -> dict[str, object]:
    """Variables of the `radar` mode of `analyst.md`: each page is untrusted content (17.4),
    cut at `TEXT_MAX` characters."""
    pages = [
        untrusted(page.text[:TEXT_MAX], f"posting {local_ref(number)}")
        for number, page in enumerate(batch, start=1)
    ]
    return {"mode": "radar", "count": len(batch), "postings": "\n\n".join(pages)}


def _tools_in_text(tools: list[str], text: str) -> list[str]:
    """The tools that appear in `text` (whole words, case- and accent-insensitive), once each."""
    kept: list[str] = []
    seen: set[str] = set()
    for tool in tools:
        key = normalize_term(tool)
        if key and key not in seen and contains_term(text, tool):
            seen.add(key)
            kept.append(tool)
    return kept


def clean_item(item: RadarItem, page: PostingPage) -> RadarFinding:
    """The extraction of `page`, checked by the code and stored under the page's marker. Not a
    posting: nothing else is kept. A posting: the tools absent from the text read and a salary
    with a figure that does not appear in it are removed (SPEC 1, 18.3)."""
    if not item.is_job_posting:
        return RadarFinding(ref=page.ref, is_job_posting=False)
    shown = page.text[:TEXT_MAX]
    tools = _tools_in_text(item.tools, shown)
    data = item.model_dump() | {
        "ref": page.ref,
        "tools": tools,
        "salary": salary_in_text(item.salary, shown),
    }
    return RadarFinding.model_validate(data)


def clean_batch(
    found: RadarBatch, batch: list[PostingPage]
) -> tuple[list[RadarFinding], list[str], int]:
    """`(stored postings, failed markers, ignored answers)`. A reference unknown to the batch or
    already given is ignored; a page the answer forgets counts as an extraction failure."""
    by_local = {local_ref(number): page for number, page in enumerate(batch, start=1)}
    kept: dict[str, RadarFinding] = {}
    ignored = 0
    for item in found.items:
        page = by_local.get(item.ref)
        if page is None or page.ref in kept:
            ignored += 1
            continue
        kept[page.ref] = clean_item(item, page)
    failed = [page.ref for page in batch if page.ref not in kept]
    return [kept[page.ref] for page in batch if page.ref in kept], failed, ignored


def pending_pages(read: list[PostingPage], extracted: frozenset[str]) -> list[PostingPage]:
    """The readable pages to extract: the first `MAX_READABLE` read, without those the port
    already reports as extracted (or failed)."""
    readable = [page for page in read if page.status == "ok"][:MAX_READABLE]
    return [page for page in readable if page.ref not in extracted]


async def _ask(deps: GraphDeps, batch: list[PostingPage]) -> tuple[RadarBatch | None, bool]:
    """`(the batch requested from the Analyst, provider failure?)`. `None` if its answer stays
    invalid after the retries, or if the provider is down (timeout, limit: second element true).
    A missing model (key gone) bubbles up: the run fails."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **radar_vars(batch))
    try:
        found = await structured_call(
            model,
            RadarBatch,
            [SystemMessage(prompt), HumanMessage(RADAR_REQUEST)],
            agent=AGENT,
            step="extraction",
            intent="reading postings from the market snapshot",
        )
    except AppError as exc:
        if exc.code in MODEL_UNAVAILABLE_CODES:
            raise
        return None, exc.code != INVALID_CODE
    return found, False


def make_extract(deps: GraphDeps) -> Node:
    @node_timeout()
    async def extract(state: MarketRadarState) -> MarketRadarState:
        """A batch of five readable, unextracted postings: one call, one storing. `extract_done`
        when this batch was the last one (computed on what the port just returned)."""
        run_id = state["run_id"]
        ctx = await deps.ports.radar.context(deps.user_id, run_id)
        pending = pending_pages(ctx.read, ctx.extracted)
        if not pending:
            return {"extract_done": True}
        batch = pending[:BATCH]
        found, provider_down = await _ask(deps, batch)
        items: list[RadarFinding] = []
        failed, ignored = [page.ref for page in batch], 0
        if found is not None:
            items, failed, ignored = clean_batch(found, batch)
        await deps.ports.radar.save_extraction(deps.user_id, deps.session_id, run_id, items, failed)
        logger.info(
            "Batch extracted: session %s, run %s, %d posting(s), %d failed, %d ignored",
            deps.session_id,
            run_id,
            len(items),
            len(failed),
            ignored,
        )
        down = state.get("failed_batches", 0) + provider_down
        return {
            "extract_done": len(pending) <= len(batch) or down >= MAX_FAILED_BATCHES,
            "failed_batches": down,
        }

    return extract


def route_extract(state: MarketRadarState) -> str:
    return "finish" if state.get("extract_done") else "extract"
