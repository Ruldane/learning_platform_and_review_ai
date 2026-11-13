"""Parcours `replan` (D105) : le Stratège propose, le code range, January choisit une option puis
accepte, refuse ou demande une autre proposition ; rejeu après un arrêt sans double écriture."""

import logging
from dataclasses import replace

import pytest

from app.agents.graphs.replan import ACCEPT_INTERRUPT, OPTION_LABELS, STALE_NOTE
from app.agents.nodes.strategist.replan_steps import (
    EMPTY_TEXT,
    IMPOSSIBLE_TEXT,
    REFUSED_TEXT,
    REPLAN_REQUEST,
)
from app.agents.tools.replan_port import ReplanContext
from app.core.errors import AppError
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.replan_support import SUMMARY, MakeReplan, ReplanRun, reply
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.replan import (
    PROGRAM_ID,
    REVIEW_TEXT,
    FakeReplanStore,
    replan_context,
    task_id,
)

FIVE_HOURS = {
    "program_id": PROGRAM_ID,
    "trigger": "message",
    "available_minutes": 300,
    "message": "Cette semaine je n'ai que 5 heures, réunion jeudi.",
}


def _models(*replies: str) -> CouncilModels:
    models = CouncilModels()
    if replies:
        models.when("strategist", REPLAN_REQUEST, *replies)
    return models


async def _proposed(run: ReplanRun, option: str) -> None:
    """Choisit `option` à la question du bilan, puis attend la proposition."""
    await run.wait_question("replan_option")
    await run.resume(option)
    await run.wait_question()


async def test_on_track_without_changes_completes_without_question(
    make_replan_runner: MakeReplan,
) -> None:
    run = await make_replan_runner()
    done = await run.wait_status("completed")
    assert await run.kinds() == [] and done.pending_interrupt is None
    assert (await run.events("run.completed"))[0]["summary"] == EMPTY_TEXT
    assert await run.said() == [REVIEW_TEXT, SUMMARY, EMPTY_TEXT]
    assert await run.events("artifact.ready") == []
    call = run.store.previews[0]
    assert call.option is None and call.draft.drop == [] and call.draft.add == []
    prompt = run.prompts()[0]
    assert "dans les temps" in prompt and REVIEW_TEXT in prompt
    assert '"drop"' not in prompt and '"add"' not in prompt  # aucun droit : un résumé seul
    assert "task-id-" not in prompt and "module-id-" not in prompt  # références seules (F7)
    assert 'source="plan à faire"' in prompt and "t5 : 23/11, Lire la doc de l'API" in prompt


async def test_late_twice_asks_option_then_proposes_with_it(
    make_replan_runner: MakeReplan,
) -> None:
    drops = reply("Je retire une lecture et une pratique.", drop=["t5", "t6", "t5"], add=[])
    run = await make_replan_runner(_models(drops), plan=replan_context("late_twice", late=2))
    first = await run.wait_question("replan_option")
    assert [o["value"] for o in first["options"]] == ["reduce_scope", "push_deadline"]
    assert [o["label"] for o in first["options"]] == [
        OPTION_LABELS["reduce_scope"],
        OPTION_LABELS["push_deadline"],
    ]
    assert first["question"].startswith("Deux semaines de suite en retard")
    await run.resume("deepen")  # pas offerte : la question revient
    await run.wait_question("replan_option")
    await run.resume("reduce_scope")
    pending = await run.wait_question()
    assert {k: pending[k] for k in ("kind", "question")} == {
        k: ACCEPT_INTERRUPT[k] for k in ("kind", "question")
    }
    assert pending["options"] == ACCEPT_INTERRUPT["options"]
    call = run.store.previews[0]
    assert call.option == "reduce_scope" and call.draft.drop == ["t5", "t6"]
    assert call.refs["t5"] == task_id("t5") and call.refs["m2"] == "module-id-m2"
    assert call.reason == "Bilan hebdomadaire ; Réduire le périmètre"
    prompt = run.prompts()[0]
    assert "Réduire le périmètre" in prompt and "2 tâche(s) en retard" in prompt
    assert '"drop"' in prompt and '"add"' not in prompt
    said = (await run.said())[-1]
    assert "1 tâche(s) retirée(s)" in said and "1 retrait(s) ignoré(s)" in said
    ready = (await run.events("artifact.ready"))[0]
    assert ready == {
        "artifact_id": PROGRAM_ID,
        "kind": "plan_version",
        "title": "Replanification : Parcours IA",
        "url": f"/apprendre/programme/{PROGRAM_ID}/replanification",
    }


async def test_ahead_offers_advance_and_deepen(make_replan_runner: MakeReplan) -> None:
    extra = {
        "module": "m2",
        "title": "Lire un article sur le RAG",
        "type": "lire",
        "minutes": 30,
        "done_criterion": "Trois idées notées",
    }
    deepen = reply("J'approfondis l'API.", drop=["t1"], add=[extra])
    run = await make_replan_runner(_models(deepen), plan=replan_context("ahead"))
    first = await run.wait_question("replan_option")
    assert [o["value"] for o in first["options"]] == ["advance", "deepen"]
    await run.resume({"option": "deepen"})
    await run.wait_question()
    call = run.store.previews[0]
    assert call.option == "deepen" and call.draft.drop == []  # aucun retrait permis
    assert [t.title for t in call.draft.add] == ["Lire un article sur le RAG"]
    assert '"add"' in run.prompts()[0] and '"drop"' not in run.prompts()[0]


async def test_accept_applies_once_after_replay(make_replan_runner: MakeReplan) -> None:
    # Arrêt du back juste après `apply` : le nœud rejoué réapplique sans effet de plus.
    first = await make_replan_runner(plan=replan_context("late_twice", late=1))
    await _proposed(first, "push_deadline")
    version = first.store.previews[0].revision + 2
    first.store.block_after_apply = True
    await first.resume("accept")
    await wait_until(lambda: first.store.apply_calls == 1)
    await first.runner.shutdown()
    first.store.block_after_apply = False
    calls = len(first.models.calls)
    second = await make_replan_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert second.store.apply_calls == 2 and second.store.applied == [version]
    assert second.prompts() == [] and len(first.models.calls) == calls  # rien d'autre rejoué
    assert len(second.store.previews) == 1
    summary = (await second.events("run.completed"))[0]["summary"]
    assert summary == f"Nouveau plan appliqué (version {version})."


def _moved_by_january() -> ReplanContext:
    """Le plan après une modification de January : « Lire la doc de l'API » (t5) n'y est plus,
    une nouvelle lecture prend sa place."""
    plan = replan_context("late_twice", late=1)
    changed = replace(plan.tasks[4], title="Lire le guide de l'API", task_id="task-id-new")
    return replace(plan, tasks=[*plan.tasks[:4], changed, *plan.tasks[5:]])


def _stale_once(store: FakeReplanStore) -> None:
    store.stale_applies = 1
    store.after_stale = _moved_by_january()


async def test_stale_apply_reproposes(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(plan=replan_context("late_twice", late=1), prepare=_stale_once)
    await _proposed(run, "push_deadline")
    await run.resume("accept")
    await run.wait_question()
    assert [c.revision for c in run.store.previews] == [0, 1]
    assert STALE_NOTE in await run.said() and STALE_NOTE in run.prompts()[1]
    assert STALE_NOTE not in run.prompts()[0]
    assert len(run.store.context_calls) == 2  # le plan est relu avant la nouvelle proposition
    # La nouvelle proposition part du plan relu : prompt et références (relecture 5.8, m2).
    assert "Lire le guide de l'API" in run.prompts()[1]
    assert "Lire la doc de l'API" not in run.prompts()[1]
    assert run.store.previews[1].refs == _moved_by_january().refs()
    assert run.store.previews[1].refs["t5"] == "task-id-new"
    assert run.store.applied == []
    await run.resume("accept")
    await run.wait_status("completed")
    assert run.store.applied == [3] and run.store.apply_calls == 2


async def test_refuse_marks_version_refused(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(plan=replan_context("late_twice", late=1))
    await _proposed(run, "push_deadline")
    await run.resume({"action": "refuse"})
    await run.wait_status("completed")
    assert run.store.refused == [2] and run.store.applied == []
    assert (await run.events("run.completed"))[0]["summary"] == REFUSED_TEXT


async def test_revise_note_is_untrusted_in_prompt(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(plan=replan_context("late_twice", late=1))
    await _proposed(run, "reduce_scope")
    for invalid in ("go", {"answers": {"note": "   "}}, {"action": "publish"}, 3):
        await run.resume(invalid)
        await run.wait_question()
    assert len(run.store.previews) == 1
    await run.resume({"answers": {"note": "Garde la pratique de l'API"}})
    await run.wait_question()
    last = run.prompts()[-1]
    assert 'source="note de January"' in last and "Garde la pratique de l'API" in last
    assert "Proposition n° 2" in last and "Réduire le périmètre" in last  # l'option reste
    assert [c.revision for c in run.store.previews] == [0, 1]
    assert run.store.previews[1].reason == (
        "Bilan hebdomadaire ; Réduire le périmètre ; proposition 2 : Garde la pratique de l'API"
    )


async def test_message_trigger_passes_week_cap(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(body=FIVE_HOURS)
    await run.wait_question()
    assert await run.kinds() == ["accept_replan"]  # aucune option hors du bilan
    call = run.store.previews[0]
    assert call.week_cap_override == 255 and call.option is None
    assert call.reason == "Message de January"
    assert run.store.context_calls[0]["available_minutes"] == 300
    prompt = run.prompts()[0]
    assert "255 min" in prompt and 'source="message de January"' in prompt
    assert "réunion jeudi" in prompt and "Bilan de la semaine" not in prompt
    assert "1 déplacée(s)" in (await run.said())[-1]


async def test_long_summary_is_shortened(make_replan_runner: MakeReplan) -> None:
    long = "Je range les retards dans les semaines suivantes. " * 20  # ~ 1 000 caractères
    run = await make_replan_runner(_models(reply(long)), body=FIVE_HOURS)
    await run.wait_question()
    summary = run.store.previews[0].draft.summary
    assert len(summary) <= 600 and summary.startswith("Je range les retards")
    assert (await run.said())[-1].startswith(summary)


async def test_impossible_week_ends_with_clear_message(make_replan_runner: MakeReplan) -> None:
    body = FIVE_HOURS | {"available_minutes": 60}  # plafond 51 : ni pratique ni quiz n'y tiennent
    run = await make_replan_runner(body=body)
    done = await run.wait_status("completed")
    assert done.error is None and await run.kinds() == []
    assert run.store.previews[0].week_cap_override == 51
    assert (await run.events("run.completed"))[0]["summary"] == IMPOSSIBLE_TEXT
    assert await run.said() == [IMPOSSIBLE_TEXT] and await run.events("artifact.ready") == []


async def test_unknown_reference_is_asked_again_then_removed(
    make_replan_runner: MakeReplan,
) -> None:
    unknown = reply("Je retire une tâche.", drop=["t99", "t5"])
    run = await make_replan_runner(_models(unknown, unknown), plan=replan_context("late_twice"))
    await _proposed(run, "reduce_scope")
    assert len(run.prompts()) == 2 and "t99" in run.prompts()[1].split(REPLAN_REQUEST)[-1]
    assert run.store.previews[0].draft.drop == ["t5"]


async def test_weekly_review_requires_its_entry(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(body=FIVE_HOURS)
    for body in (
        {"program_id": PROGRAM_ID, "trigger": "weekly_review"},
        FIVE_HOURS | {"available_minutes": 30},
    ):
        with pytest.raises(AppError) as error:
            await run.runner.start(run.user_id, "replan", body)
        assert error.value.code == "invalid_input"


async def test_logs_carry_ids_only(
    make_replan_runner: MakeReplan, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    secret = reply("Résumé secret du Stratège.", drop=["t5"])
    run = await make_replan_runner(_models(secret, secret), plan=replan_context("late_twice"))
    await _proposed(run, "reduce_scope")
    await run.resume({"answers": {"note": "Note privée de January"}})
    await run.wait_question()
    await run.resume("accept")
    await run.wait_status("completed")
    for text in ("Résumé secret", "Note privée", "Lire la doc", "Bases de Python", REVIEW_TEXT):
        assert text not in caplog.text
    assert run.sid in caplog.text and PROGRAM_ID in caplog.text
