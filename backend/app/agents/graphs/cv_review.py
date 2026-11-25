"""`cv_review` graph (SPEC 5.3, F9, D129): the ATS Reader and the Recruiter review January's CV
against a posting, confront each other in at most two rounds, then the code validates each
proposal against the master profile and stores the review; January then chooses the output.

START -> load -> (analysis stored ? company : analyze)
analyze -> (job posting ? save_analysis -> company : not_a_posting, readable failure)
company -> ats_reader -> recruiter -> confront_1 -> confront_2 -> validate -> save -> ask_output
ask_output: `interrupt()` alone; invalid answer -> ask_output (same question)
apply_output: report or PDF -> ask_output; Finish -> close -> END

`analyze` and `save_analysis` are the Analyst's nodes (6.5): a posting already analysed is
never analysed again (D121; branch unreachable in practice, the route refuses a posting that is
not ready). Launched only by the route of the `cv` feature (6.14). Every port write is idempotent
(SPEC 9.4) and `durability="sync"` (D46) never replays a finished node."""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.analyst import make_analyze, make_save_analysis
from app.agents.nodes.ats_reader import Node, make_ats_reader
from app.agents.nodes.recruiter import make_recruiter
from app.agents.nodes.review_confront import make_confront
from app.agents.nodes.review_output import (
    ask_output,
    make_apply_output,
    make_close,
    route_apply,
    route_output,
)
from app.agents.nodes.review_save import make_save, make_validate
from app.agents.nodes.scout.company import make_company
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.cv_review import CvReviewState
from app.core.errors import AppError

__all__ = ["NOT_A_POSTING", "CvReviewInput", "build"]

NOT_A_POSTING = "The CV review needs a job posting. The supplied text doesn't look like one."

logger = logging.getLogger(__name__)


class CvReviewInput(BaseModel):
    review_id: str = Field(min_length=36, max_length=36)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: CvReviewState) -> CvReviewState:
        ctx = await deps.ports.cv_review.context(deps.user_id, state["review_id"])
        logger.info(
            "Review read: session %s, review %s, posting %s, analysis stored %s",
            deps.session_id,
            ctx.review_id,
            ctx.posting_id,
            ctx.analysis is not None,
        )
        analysis = ctx.analysis.model_dump(mode="json") if ctx.analysis else None
        return {"posting_id": ctx.posting_id, "analysis": analysis, "company": ctx.company}

    return load


def route_load(state: CvReviewState) -> str:
    return "company" if state.get("analysis") else "analyze"


def route_analyze(state: CvReviewState) -> str:
    analysis = state.get("analysis") or {}
    return "save_analysis" if analysis.get("is_job_posting") else "not_a_posting"


def not_a_posting(state: CvReviewState) -> CvReviewState:
    """Readable failure: without an analysed posting, no review (nothing is written)."""
    raise AppError("posting_not_a_job", NOT_A_POSTING, 422)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CvReviewState)
    nodes: dict[str, Any] = {
        "load": make_load(deps),
        "analyze": make_analyze(deps),
        "save_analysis": make_save_analysis(deps),
        "not_a_posting": not_a_posting,
        "company": make_company(deps),
        "ats_reader": make_ats_reader(deps),
        "recruiter": make_recruiter(deps),
        "confront_1": make_confront(deps, 1),
        "confront_2": make_confront(deps, 2),
        "validate": make_validate(deps),
        "save": make_save(deps),
        "ask_output": ask_output,
        "apply_output": make_apply_output(deps),
        "close": make_close(deps),
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    for source, target in [
        (START, "load"),
        ("save_analysis", "company"),
        ("company", "ats_reader"),
        ("ats_reader", "recruiter"),
        ("recruiter", "confront_1"),
        ("confront_1", "confront_2"),
        ("confront_2", "validate"),
        ("validate", "save"),
        ("save", "ask_output"),
        ("not_a_posting", END),
        ("close", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("load", route_load, ["company", "analyze"])
    graph.add_conditional_edges("analyze", route_analyze, ["save_analysis", "not_a_posting"])
    graph.add_conditional_edges("ask_output", route_output, ["apply_output", "ask_output"])
    graph.add_conditional_edges("apply_output", route_apply, ["close", "ask_output"])
    return graph
