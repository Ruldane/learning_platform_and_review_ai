"""Parcours `hiring_committee` (D147), reprises et journaux : un redémarrage ne revote pas et ne
range pas deux fois, un refus du port fait échouer la session lisiblement, les journaux ne citent
ni CV, ni offre, ni parole, ni entreprise."""

import logging
import re

import pytest

from app.agents.nodes.committee.common import DEBATE_REQUEST, SYNTHESIS_REQUEST, VOTE_REQUEST
from app.core.errors import AppError
from tests.agents.graphs.committee_support import MakeCommittee, committee, prompts
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.committee import FakeCommitteeStore


async def test_committee_replay_votes_once(
    committee_runner: MakeCommittee, committee_store: FakeCommitteeStore
) -> None:
    """Arrêt du back pendant le rangement : le nœud rejoué relit l'issue de sa session ; aucun
    vote, aucune parole, aucune synthèse n'est redemandé et l'issue n'est rangée qu'une fois."""
    committee_store.block_after_save = True
    first = await committee_runner()
    await wait_until(lambda: committee_store.save_calls == 1)
    assert len(prompts(first.models, "manager", VOTE_REQUEST)) == 1
    await first.runner.shutdown()
    committee_store.block_after_save = False
    second = await committee_runner(committee(), sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert committee_store.save_calls == 2 and len(committee_store.saved) == 1
    assert second.models.calls == []  # ni parole, ni vote, ni synthèse redemandés
    votes = [c for c in first.models.calls if VOTE_REQUEST in c.prompt]
    assert len(votes) == 4 and len(first.models.calls) == 17
    assert len(prompts(first.models, "moderator", SYNTHESIS_REQUEST)) == 1
    assert [v.persona for v in committee_store.only.votes] == [
        "ats_reader",
        "recruiter",
        "manager",
        "colleague",
    ]
    assert committee_store.context_calls == 1  # le contexte n'est pas relu au redémarrage


async def test_restart_during_debate_does_not_vote(
    committee_runner: MakeCommittee, committee_store: FakeCommitteeStore
) -> None:
    """Arrêt pendant le débat : au redémarrage, le comité reprend sans avoir voté ; les votes ne
    sont demandés qu'une fois, après le débat."""
    first_models = committee()

    first_models.block = lambda agent, prompt: DEBATE_REQUEST in prompt and "tour 2 sur 2" in prompt
    first = await committee_runner(first_models)
    await wait_until(lambda: first_models.blocked >= 1)
    assert [c for c in first_models.calls if VOTE_REQUEST in c.prompt] == []
    await first.runner.shutdown()
    second = await committee_runner(committee(), sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert len([c for c in second.models.calls if VOTE_REQUEST in c.prompt]) == 4
    assert len(committee_store.saved) == 1 and committee_store.save_calls == 1


async def test_store_refusal_fails_with_its_message(
    committee_runner: MakeCommittee, committee_store: FakeCommitteeStore
) -> None:
    async def refuse(*args: object, **kwargs: object) -> None:
        raise AppError("committee_not_found", "Comité introuvable.", 404)

    committee_store.context = refuse  # type: ignore[method-assign]
    run = await committee_runner()
    await run.wait_status("failed")
    assert await run.failed_code() == "committee_not_found"
    assert run.models.calls == [] and committee_store.save_calls == 0


async def test_committee_never_logged(
    caplog: pytest.LogCaptureFixture,
    committee_runner: MakeCommittee,
    committee_store: FakeCommitteeStore,
) -> None:
    caplog.set_level(logging.INFO)  # pas le SQL d'aiosqlite, qui cite la ligne de la session
    caplog.set_level(logging.DEBUG, logger="app")
    secrets = (
        "CV ultra secret",
        "Offre ultra secrète",
        "Parole ultra secrète",
        "Entreprise Ultra Secrète",
        "Intitulé Ultra Secret",
        "ultra-secret.example.org",
    )
    committee_store.update(
        cv_text=f"{secrets[0]} https://{secrets[5]}/cv",
        posting_text=f"{secrets[1]} https://{secrets[5]}/offre",
        company=secrets[3],
        title=secrets[4],
    )
    speeches = {"manager": f"Je réponds au Recruteur : {secrets[2]}."}
    run = await committee_runner(committee(speeches=speeches))
    await run.wait_status("completed")
    assert run.sid in caplog.text and "verdict yes" in caplog.text
    for secret in secrets:
        assert secret not in caplog.text
        assert secret.lower() not in caplog.text.lower()


async def test_one_unreadable_vote_fails_the_committee_without_saving(
    committee_runner: MakeCommittee, committee_store: FakeCommitteeStore
) -> None:
    """Un vote illisible après les nouveaux essais fait échouer la session : aucun vote de repli
    n'est inventé, la synthèse n'est pas demandée et rien n'est rangé."""
    models = committee()
    models.when("manager", VOTE_REQUEST, "pas du JSON", "pas du JSON", "pas du JSON")
    models.rules.insert(0, models.rules.pop())  # la règle du test passe avant la règle par défaut
    run = await committee_runner(models)
    await run.wait_status("failed")
    assert await run.failed_code() == "structured_output_invalid"
    assert prompts(models, "moderator", SYNTHESIS_REQUEST) == []
    assert committee_store.save_calls == 0


async def test_vote_values_never_logged(
    caplog: pytest.LogCaptureFixture, committee_runner: MakeCommittee
) -> None:
    """M5 : le journal des votes dit la session et le nombre de votes, jamais ce que chaque persona
    a voté (oui, non, peut_etre) ; le verdict, résultat du comité, reste journalisé à part."""
    caplog.set_level(logging.INFO, logger="app")
    votes = {"ats_reader": "no", "recruiter": "maybe", "manager": "yes", "colleague": "no"}
    run = await committee_runner(committee(votes=votes))
    await run.wait_status("completed")
    [record] = [r for r in caplog.records if r.name == "app.agents.nodes.committee.votes"]
    text = record.getMessage()
    assert run.sid in text and "4 vote(s)" in text
    for persona in votes:
        assert persona not in text
    assert not re.search(r"\b(yes|no|maybe)\b", text)
    assert not re.search(r"=(yes|no|maybe)\b", caplog.text)
