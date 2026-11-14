"""Le Lecteur ATS (SPEC 5.3, F9, D129) : il relit le CV comme un logiciel de recrutement le lirait
(mots clés de l'offre, intitulés de sections, ordre) et propose des modifications adossées aux
faits du profil maître (références `a1`, `a2`…). Il connaît la base datée des ATS
(`_shared/ats_base.md`) ; aucune garantie de passage n'est promise.

Le nœud n'écrit rien : ses propositions passent par l'état, puis par la confrontation et le
validateur. Journaux : identifiants et nombres seulement (17.2)."""

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
        """Rejoué après un arrêt, il redemande sans rien écrire (l'état n'a rien gardé)."""
        ctx, _, variables = await review_inputs(deps, state)
        reading, kept = await ask_proposals(deps, AGENT, AtsReading, variables, ctx.profile)
        return {
            "proposals": [p.model_dump(mode="json") for p in kept],
            "ats_notes": list(reading.notes),
        }

    return ats_reader
