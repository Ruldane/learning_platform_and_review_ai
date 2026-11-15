"""L'avant et l'après du comité (SPEC F19, D147) : pur, sans base ni modèle. Les votes sont
comparés persona par persona ; les objections après normalisation (casse, accents, ponctuation) :
deux objections dont la ressemblance atteint 0,85 sont la même (`SIMILAR`)."""

from collections.abc import Sequence
from difflib import SequenceMatcher

from app.agents.tools.committee_schema import PERSONAS, PersonaVote
from app.agents.tools.posting_schema import normalize_term
from app.features.applications.schemas_committee import CommitteeDiff, VoteChange

SIMILAR = 0.85


def same_objection(first: str, second: str) -> bool:
    """Même objection : texte normalisé identique, ou ressemblance d'au moins `SIMILAR`."""
    one, two = normalize_term(first), normalize_term(second)
    return one == two or SequenceMatcher(None, one, two).ratio() >= SIMILAR


def _absent_from(texts: Sequence[str], others: Sequence[str]) -> list[str]:
    return [text for text in texts if not any(same_objection(text, other) for other in others)]


def committee_diff(
    previous_id: str,
    before: Sequence[PersonaVote],
    after: Sequence[PersonaVote],
    objections_before: Sequence[str],
    objections_after: Sequence[str],
) -> CommitteeDiff:
    """Ce qui a changé de l'exécution `previous_id` (avant) à celle-ci (après) : le vote de chaque
    persona présente dans les deux, les objections qui ont disparu et celles qui sont nouvelles."""
    old = {vote.persona: vote.vote for vote in before}
    new = {vote.persona: vote.vote for vote in after}
    return CommitteeDiff(
        previous_id=previous_id,
        votes=[
            VoteChange(persona=persona, before=old[persona], after=new[persona])
            for persona in PERSONAS
            if persona in old and persona in new
        ],
        objections_resolved=_absent_from(objections_before, objections_after),
        objections_new=_absent_from(objections_after, objections_before),
    )
