"""Before and after the committee (SPEC F19, D147): pure, with no database or model. Votes are
compared persona by persona; objections after normalization (case, accents, punctuation): two
objections whose similarity reaches 0.85 are the same (`SIMILAR`)."""

from collections.abc import Sequence
from difflib import SequenceMatcher

from app.agents.tools.committee_schema import PERSONAS, PersonaVote
from app.agents.tools.posting_schema import normalize_term
from app.features.applications.schemas_committee import CommitteeDiff, VoteChange

SIMILAR = 0.85


def same_objection(first: str, second: str) -> bool:
    """Same objection: identical normalized text, or similarity of at least `SIMILAR`."""
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
    """What changed from the `previous_id` run (before) to this one (after): the vote of each
    persona present in both, and the objections that disappeared or are new."""
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
