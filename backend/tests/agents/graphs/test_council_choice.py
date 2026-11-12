"""Propositions du Stratège et choix de January (point d'arrêt n° 2, D85) : lot de 2 à 3, nouveau
tour, choix invalide, mélange, rejeu après un arrêt du back, plafond de tokens, journaux."""

import asyncio
import json
import logging
from datetime import date

import pytest

from app.agents.nodes.council_choice import ChoiceAnswer, parse_choice
from app.agents.runtime.repositories import SessionRepository
from tests.agents.graphs.council_models import CouncilModels, proposal
from tests.agents.graphs.council_support import Council, MakeCouncil
from tests.agents.runtime.runner_helpers import all_events, get_session, wait_until

CHOOSE_PATH = {
    "kind": "choose_path",
    "question": (
        "Choisis un parcours dans l'onglet Propositions, mélange-en deux, ou demande un autre tour."
    ),
    "options": [{"value": "another_round", "label": "Demander un autre tour"}],
}


async def _ids(c: Council) -> list[str]:
    return [p["proposal_id"] for p in await c.events("proposal.ready")]


async def test_two_to_three_proposals_then_choice_interrupt(
    make_council_runner: MakeCouncil,
) -> None:
    models = CouncilModels()
    four = json.dumps({"proposals": [proposal(f"Parcours {n}") for n in range(4)]})
    three = json.dumps({"proposals": [proposal(f"Parcours {n}") for n in range(3)]})
    models.when("strategist", "Propose les parcours.", four, three)
    c = await make_council_runner(models=models)
    await c.to_choice()
    ready = await c.events("proposal.ready")
    assert len(ready) in (2, 3) and c.pending is not None and c.pending["kind"] == "choose_path"
    assert [r["title"] for r in ready] == ["Parcours 0", "Parcours 1", "Parcours 2"]
    assert {k: c.pending[k] for k in CHOOSE_PATH} == CHOOSE_PATH
    assert list(c.store.batches) == [(c.sid, 1)]
    assert c.store.minutes  # compte rendu gardé sur l'objectif
    propose_prompt = next(
        call.prompt for call in models.calls if "Propose les parcours." in call.prompt
    )
    assert "Le Conseil s'accorde" in propose_prompt  # le Stratège part du compte rendu


async def test_another_round_returns_to_debate_then_new_batch(
    make_council_runner: MakeCouncil,
) -> None:
    c = await make_council_runner()
    first = await c.to_choice()
    await c.resume("another_round")
    second = await c.wait_choice(after=first)
    assert len(await c.agent_messages(step_prefix="tour-3")) == 4  # retour au débat, un tour
    assert list(c.store.batches) == [(c.sid, 1), (c.sid, 2)]
    ids = await _ids(c)
    assert len(ids) == 4 and len(set(ids)) == 4  # nouvelles propositions
    assert len(c.store.boards) == 9  # les étapes du tableau continuent, sans écraser
    await c.resume({"action": "choose", "proposal_ids": [ids[0]]})  # lot précédent : refusé
    await c.wait_choice(after=second)
    await c.resume({"action": "choose", "proposal_ids": [ids[2]]})
    await c.wait_status("completed")
    assert [choice.proposal_ids for choice in c.store.choices] == [(ids[2],)]


async def test_commands_sent_while_choosing_do_not_change_the_new_round(
    make_council_runner: MakeCouncil,
) -> None:
    # Revue 4.4 : « Passer aux propositions » et « Relancer un tour » envoyés pendant l'attente du
    # choix, puis « autre tour » : un seul tour de plus, joué en entier ; le texte reste lu.
    c = await make_council_runner()
    first = await c.to_choice()
    await c.post_message("", "to_proposals")
    await c.post_message("", "another_round")
    await c.post_message("Plus de pratique, merci")
    await c.resume("another_round")
    await c.wait_choice(after=first)
    third_round = await c.agent_messages(step_prefix="tour-3")
    assert len(third_round) == 4 and await c.agent_messages(step_prefix="tour-4") == []
    assert "Plus de pratique" in c.prompt_of(third_round[0])
    assert list(c.store.batches) == [(c.sid, 1), (c.sid, 2)]


async def test_invalid_choice_asks_again(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner()
    first = await c.to_choice()
    await c.resume({"action": "choose", "proposal_ids": ["inconnue"]})
    again = await c.wait_choice(after=first)
    assert {k: again[k] for k in CHOOSE_PATH} == CHOOSE_PATH
    assert c.store.choices == [] and c.store.programs_started == 0
    p1 = (await _ids(c))[0]
    await c.resume({"action": "choose", "proposal_ids": [p1]})
    final = await c.wait_status("completed")
    assert c.store.choices[-1].proposal_ids == (p1,) and c.store.programs_started == 1
    assert final.pending_interrupt is None


async def test_mix_records_two_proposals_and_starts_program(
    make_council_runner: MakeCouncil,
) -> None:
    c = await make_council_runner()
    await c.to_choice()
    p1, p2 = await _ids(c)
    await c.resume({"action": "mix", "proposal_ids": [p1, p2], "start_date": "2026-11-16"})
    await c.wait_status("completed")
    assert c.store.choices[-1].proposal_ids == (p1, p2) and c.store.programs_started == 1
    assert c.store.choices[-1].action == "mix"
    assert c.store.choices[-1].start_date == date(2026, 11, 16)
    done = await c.events("run.completed")
    assert "Parcours pratique" in done[0]["summary"] and "Parcours socle" in done[0]["summary"]


async def test_council_replay_does_not_duplicate_boards_or_proposals(
    make_council_runner: MakeCouncil,
) -> None:
    # Arrêt du back en plein `proposal_boards` : les frises sont écrites, la comparaison se fige.
    models = CouncilModels()
    models.block = lambda agent, prompt: agent == "scribe" and "comparaison des parcours" in prompt
    first = await make_council_runner(models=models)
    await first.wait_question("framing")
    await first.resume("go")
    await wait_until(lambda: models.blocked == 1)
    boards_before_restart = len(first.store.boards)
    assert boards_before_restart == 4  # carte, prérequis, deux frises
    await first.runner.shutdown()
    second = await make_council_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_choice()
    expected_rest = 1  # la comparaison ; les frises rejouées retrouvent leur étape
    assert len(second.store.boards) == boards_before_restart + expected_rest
    assert len(second.store.batches) == 1 and len(second.store.attached) == 2
    assert len(await second.events("proposal.ready")) == 2  # `propose` n'est pas rejoué


async def test_replayed_propose_reads_the_saved_batch(make_council_runner: MakeCouncil) -> None:
    # Arrêt du back juste après l'écriture du lot : `propose` rejoué relit le lot enregistré
    # (noms et détails ensemble) au lieu de rappeler le Stratège (revue 4.4, Minor 3).
    models = CouncilModels()
    first_batch = [proposal("Premier A"), proposal("Premier B")]
    first_batch[0]["promise"] = "Promesse propre au premier lot."
    models.when("strategist", "Propose les parcours.", json.dumps({"proposals": first_batch}))
    first = await make_council_runner(models=models)
    first.store.block_after_proposals = True
    await first.wait_question("framing")
    await first.resume("go")
    await wait_until(lambda: first.store.proposals_calls == 1)
    await first.runner.shutdown()
    first.store.block_after_proposals = False
    second = await make_council_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_choice()
    assert not any("Propose les parcours." in call.prompt for call in second.models.calls)
    assert [r["title"] for r in await second.events("proposal.ready")] == ["Premier A", "Premier B"]
    timeline = next(call.prompt for call in second.models.calls if "Nom : Premier A" in call.prompt)
    assert "Promesse propre au premier lot." in timeline
    assert second.store.proposals_calls == 1 and len(second.store.batches) == 1


async def test_token_cap_fails_council_readably(make_council_runner: MakeCouncil) -> None:
    cap = 50_000
    c = await make_council_runner(token_cap=cap)

    async def exhaust(agent: str, prompt: str) -> None:
        if agent == "practitioner":  # 2e orateur du tour 1 : l'appel suivant est refusé
            async with c.web.factory() as db:
                await SessionRepository(db, c.user_id).add_usage(
                    c.sid, tokens_in=cap, tokens_out=0, cost_usd=0.0
                )
                await db.commit()
            c.models.hooks.clear()

    c.models.hooks.append(exhaust)
    await c.wait_question("framing")
    await c.resume("go")
    row = await c.wait_status("failed")
    assert row.error is not None and row.error["code"] == "token_cap_reached"
    failed = await c.events("run.failed")
    assert failed[-1]["code"] == "token_cap_reached" and "Plafond" in failed[-1]["message"]
    assert await c.events("proposal.ready") == []


async def test_logs_never_contain_debate_content(
    make_council_runner: MakeCouncil, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    models = CouncilModels()
    bad = '{"title": "Carte secrète", "mermaid": "sequenceDiagram\\nA->>B: x"}'
    models.when("scribe", "dessiner la carte du domaine", bad, bad)
    models.when("practitioner", "Tour en cours : 2\n", "Avis sans nom ni source.", "Toujours.")
    c = await make_council_runner(models=models)
    await c.wait_question("framing")
    await c.resume("go")
    await asyncio.sleep(0)
    await c.post_message("Note privée de January")
    await c.wait_choice()
    p1 = (await _ids(c))[0]
    await c.resume({"action": "choose", "proposal_ids": [p1]})
    await c.wait_status("completed")
    for secret in ("Note privée", "Carte secrète", "Parcours pratique", "Avis sans nom"):
        assert secret not in caplog.text
    assert c.sid in caplog.text  # les écarts sont journalisés, par identifiants


def test_parse_choice() -> None:
    batch = ["a", "b", "c"]
    assert parse_choice("another_round", batch) == ChoiceAnswer(action="another_round")
    assert parse_choice({"action": "another_round", "proposal_ids": ["a"]}, batch) == ChoiceAnswer(
        action="another_round"
    )
    assert parse_choice({"action": "choose", "proposal_ids": ["b"]}, batch) is not None
    assert parse_choice({"action": "choose", "proposal_ids": ["a", "b"]}, batch) is None
    assert parse_choice({"action": "choose", "proposal_ids": ["z"]}, batch) is None
    assert parse_choice({"action": "mix", "proposal_ids": ["a", "c"]}, batch) is not None
    assert parse_choice({"action": "mix", "proposal_ids": ["a", "a"]}, batch) is None
    assert parse_choice({"action": "mix", "proposal_ids": ["a", "b", "c"]}, batch) is None
    assert (
        parse_choice({"action": "choose", "proposal_ids": ["a"], "start_date": "x"}, batch) is None
    )
    assert parse_choice("go", batch) is None and parse_choice(None, batch) is None


async def test_session_row_keeps_no_choice_until_valid(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner()
    await c.to_choice()
    row = await get_session(c.web.factory, c.user_id, c.sid)
    assert row.status == "waiting_user"
    types = [e.type for e in await all_events(c.web.factory, c.user_id, c.sid)]
    assert types.count("interrupt.requested") == 2  # cadrage, puis choix
