"""Le Recruteur (SPEC 5.3, F9, D129) : il relit le CV comme une personne qui recrute pour cette
offre (impact, clarté, longueur) et propose des modifications adossées aux faits du profil maître
(références `r1`, `r2`…), avec les forces et les risques du CV pour le rapport.

Le nœud n'écrit rien : ses propositions rejoignent celles du Lecteur ATS dans l'état. Journaux :
identifiants et nombres seulement (17.2)."""

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
