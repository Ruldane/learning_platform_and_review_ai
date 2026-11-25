"""Parcours `hiring_committee` (D147), flux live : ce que January voit défiler dans la session
(impressions, débat, votes, synthèse, clôture) et le contexte de test valable."""

from app.agents.tools.committee_schema import PERSONAS
from tests.agents.graphs.committee_support import (
    IMPRESSIONS,
    OBJECTIONS,
    MakeCommittee,
    committee,
)
from tests.support.committee import COMPANY, default_context


async def test_votes_are_announced_in_the_live_feed(committee_runner: MakeCommittee) -> None:
    """Chaque persona annonce son vote (`agent.message`, id `<persona>-vote`) avec son objection ;
    le Modérateur publie la synthèse puis la clôture (« simulation, pas une prédiction »)."""
    run = await committee_runner(committee(votes={"manager": "no", "colleague": "maybe"}))
    await run.wait_status("completed")
    events = await run.events("agent.message")
    ids = {e["message_id"] for e in events}
    assert {f"{persona}-vote" for persona in PERSONAS} <= ids
    wording = {
        "ats_reader": "yes, I'd offer an interview",
        "recruiter": "yes, I'd offer an interview",
        "manager": "no, I wouldn't move forward",
        "colleague": "maybe, I'd like to know more",
    }
    for persona in PERSONAS:
        [text] = [m for m in await run.messages(persona) if m.startswith("I vote")]
        assert wording[persona] in text and OBJECTIONS[persona] in text
    assert {"moderator-synthese", "moderator-fin"} <= ids
    synthesis, closing = await run.messages("moderator")
    assert synthesis.startswith("The committee voted maybe.")
    assert "The simulated hiring committee voted maybe" in closing


async def test_impressions_come_first_in_the_feed(committee_runner: MakeCommittee) -> None:
    run = await committee_runner()
    await run.wait_status("completed")
    for persona in PERSONAS:
        assert (await run.messages(persona))[0] == IMPRESSIONS[persona]


def test_default_context_exposes_the_ats_terms() -> None:
    ctx = default_context()
    assert ctx.company == COMPANY and "LangGraph" in ctx.ats_terms.missing
    assert "Python" in ctx.ats_terms.found
