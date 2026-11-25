"""The Recruiter (SPEC 5.3, F9, D129): it rereads the CV as a person hiring for this posting
would (impact, clarity, length) and proposes changes backed by facts from the master profile
(references `r1`, `r2`...), with the CV's strengths and risks for the report.

The node writes nothing: its proposals join the ATS Reader's in the state. Logs: identifiers and
numbers only (17.2)."""

from typing import Protocol

from app.agents.nodes.review_common import PROPOSE_TIMEOUT_S, ask_proposals, review_inputs
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.review_schema import RecruiterReading

AGENT = "recruiter"


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def make_recruiter(deps: GraphDeps) -> Node:
    @node_timeout(PROPOSE_TIMEOUT_S)
    async def recruiter(state: CvReviewState) -> CvReviewState:
        ctx, _, variables = await review_inputs(deps, state)
        reading, kept = await ask_proposals(deps, AGENT, RecruiterReading, variables, ctx.profile)
        mine = [p.model_dump(mode="json") for p in kept]
        return {
            "proposals": [*state.get("proposals", []), *mine],
            "strengths": list(reading.strengths),
            "risks": list(reading.risks),
        }

    return recruiter
