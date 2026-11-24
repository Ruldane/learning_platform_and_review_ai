"""Parcours `cv_review` (SPEC 5.3, F9, D129) : le Lecteur ATS et le Recruteur relisent le CV de
January contre une offre, se confrontent en deux tours au plus, puis le code valide chaque
proposition contre le profil maître et range la revue ; January choisit ensuite la sortie.

START -> load -> (analyse rangée ? company : analyze)
analyze -> (offre d'emploi ? save_analysis -> company : not_a_posting, échec lisible)
company -> ats_reader -> recruiter -> confront_1 -> confront_2 -> validate -> save -> ask_output
ask_output : `interrupt()` seul ; réponse invalide -> ask_output (même question)
apply_output : rapport ou PDF -> ask_output ; Terminer -> close -> END

`analyze` et `save_analysis` sont les nœuds de l'Analyste (6.5) : une offre déjà analysée n'est
jamais réanalysée (D121 ; branche inatteignable en pratique, la route refuse une offre non prête).
Lancé seulement par la route de la feature `cv` (6.14). Chaque écriture d'un port est idempotente
(SPEC 9.4) et `durability="sync"` (D46) ne rejoue jamais un nœud terminé."""

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
            "Revue lue : session %s, revue %s, offre %s, analyse rangée %s",
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
    """Échec lisible : sans offre analysée, aucune revue (rien n'est écrit)."""
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
