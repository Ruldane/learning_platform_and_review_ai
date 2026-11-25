"""Graph `project_review` (P2 to P4, D165): the Practitioner assesses a mini project submission
against the brief's criteria; the code decides the verdict; if validated, it writes the four drafts
for January, which the code checks (`text_claims`).

START -> load -> read_repo -> (nothing to read? skip : evaluate)
skip -> save; evaluate -> (validated ? drafts : save); drafts -> (to fix ? redo : save)
redo -> save -> announce -> END

Mode `drafts` (D173 no. 4, D181): a project **already validated** without its drafts (their write
had failed): `load -> seed -> drafts -> (to fix ? redo : save)`, with no repository read nor
evaluation; `save` only stores the drafts (`save_drafts`). Same caps: one standard call
and one retry at most.

Without a description or a readable repository, no model call: "to redo", never "validated" on
nothing. No interruption, no loop; each node rereads its inputs through the port, and the port write
is idempotent per session (SPEC 9.4). Three standard calls at most (evaluation,
drafts, one new try of the drafts in its own node and its own timeout: its failure
keeps the first draft "to verify"). Started only by the `projects` feature (8.10,
`ROUTE_ONLY`)."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.practitioner.drafts import make_drafts, make_redo, route_drafts
from app.agents.nodes.practitioner.drafts_only import make_seed, route_load
from app.agents.nodes.practitioner.evaluate import (
    NO_REPO_FEEDBACK,
    make_evaluate,
    make_load,
    make_read_repo,
    make_skip,
    route_evaluate,
    route_read,
)
from app.agents.nodes.practitioner.finish import announce, make_save
from app.agents.runtime.deps import GraphDeps
from app.agents.state.project_review import ProjectReviewState

__all__ = ["NO_REPO_FEEDBACK", "ProjectReviewInput", "build"]


class ProjectReviewInput(BaseModel):
    project_id: str = Field(min_length=36, max_length=36)
    mode: Literal["review", "drafts"] = "review"


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ProjectReviewState)
    graph.add_node("load", make_load(deps))
    graph.add_node("read_repo", make_read_repo(deps))
    graph.add_node("seed", make_seed(deps))
    graph.add_node("skip", make_skip(deps))
    graph.add_node("evaluate", make_evaluate(deps))
    graph.add_node("drafts", make_drafts(deps))
    graph.add_node("redo", make_redo(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("announce", announce)
    for source, target in [
        (START, "load"),
        ("seed", "drafts"),
        ("skip", "save"),
        ("redo", "save"),
        ("save", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("load", route_load, ["read_repo", "seed"])
    graph.add_conditional_edges("read_repo", route_read, ["skip", "evaluate"])
    graph.add_conditional_edges("evaluate", route_evaluate, ["drafts", "save"])
    graph.add_conditional_edges("drafts", route_drafts, ["redo", "save"])
    return graph
