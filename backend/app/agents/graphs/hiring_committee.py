"""Graph `hiring_committee` (SPEC F19, 9.3, D147): the simulated hiring committee. Four
personas read the CV of a ready version against the offer, give their first impression,
debate for two rounds and vote; the Moderator ranks the objections and proposes three changes.

START -> load -> impressions -> round_1 -> round_2 -> votes -> synthesis -> save -> END

17 calls at most: 4 impressions, 4 speeches in round 1, 4 in round 2, 4 votes, 1 summary.
What the code decides: the speaking order (fixed rotation), the verdict (majority of votes; a tie
or no majority: "maybe") and the "to acquire" terms of the changes. No
`interrupt()` (January watches the committee debate). `save` is the only write, idempotent per
session (SPEC 9.4); `durability="sync"` (D46) never replays a finished node, so never a
given vote.
Started only by the `applications` feature route (7.10, `ROUTE_ONLY`)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.committee import (
    make_impressions,
    make_load,
    make_round,
    make_save,
    make_synthesis,
    make_votes,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.hiring_committee import HiringCommitteeState

__all__ = ["HiringCommitteeInput", "build"]


class HiringCommitteeInput(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(HiringCommitteeState)
    nodes: dict[str, Any] = {
        "load": make_load(deps),
        "impressions": make_impressions(deps),
        "round_1": make_round(deps, 1),
        "round_2": make_round(deps, 2),
        "votes": make_votes(deps),
        "synthesis": make_synthesis(deps),
        "save": make_save(deps),
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    chain = [START, *nodes, END]
    for source, target in zip(chain, chain[1:], strict=False):
        graph.add_edge(source, target)
    return graph
