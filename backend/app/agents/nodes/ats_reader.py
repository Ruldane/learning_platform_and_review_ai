"""The ATS Reader (SPEC 5.3, F9, D129): it rereads the CV as recruiting software would
(posting keywords, section headings, order) and proposes changes backed by facts from the master
profile (references `a1`, `a2`...). It knows the dated ATS base (`_shared/ats_base.md`); no
guarantee of passing is promised.

The node writes nothing: its proposals go through the state, then the confrontation and the
validator. Logs: identifiers and numbers only (17.2)."""

from typing import Protocol

from app.agents.nodes.review_common import PROPOSE_TIMEOUT_S, ask_proposals, review_inputs
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.review_schema import AtsReading

AGENT = "ats_reader"


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def make_ats_reader(deps: GraphDeps) -> Node:
    @node_timeout(PROPOSE_TIMEOUT_S)
    async def ats_reader(state: CvReviewState) -> CvReviewState:
        """Replayed after a stop, it asks again without writing anything
        (the state kept nothing)."""
        ctx, _, variables = await review_inputs(deps, state)
        reading, kept = await ask_proposals(deps, AGENT, AtsReading, variables, ctx.profile)
        return {
            "proposals": [p.model_dump(mode="json") for p in kept],
            "ats_notes": list(reading.notes),
        }

    return ats_reader
