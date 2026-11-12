"""Parcours `program_builder` (D86) : le Stratège écrit le programme, les règles de 4.2 le
vérifient et le rangent, January le valide ou demande une révision (point d'arrêt n° 3) ; rejeu
après un arrêt du back sans double écriture."""

import json
import logging

import pytest

from app.agents.nodes.strategist.plan import ValidationAnswer, parse_validation
from app.core.errors import AppError
from app.features.program.service.budget import Budget
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.program_support import PLAN_REQUEST, Builder, MakeBuilder
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.council import GOAL_ID
from tests.support.program import full_week, module, plan, task, week

VALIDATE_PROGRAM = {
    "kind": "validate_program",
    "question": (
        "Déplace, supprime ou ajoute des tâches dans le calendrier, puis valide le programme ou "
        "demande une révision."
    ),
    "options": [{"value": "validate", "label": "Valider le programme"}],
}
OVER = plan([full_week("Bases", [120] * 8)]).model_dump_json()  # 1 025 min > 714


def _models(*replies: str) -> CouncilModels:
    models = CouncilModels()
    if replies:
        models.when("strategist", PLAN_REQUEST, *replies)
    return models


async def _program_id(c: Builder) -> str:
    return str((await c.events("artifact.ready"))[0]["artifact_id"])


async def test_builder_saves_draft_and_stops_for_validation(
    make_builder_runner: MakeBuilder,
) -> None:
    c = await make_builder_runner()
    pending = await c.wait_question()
    assert pending["kind"] == "validate_program" and c.store.drafts[0].revision == 0
    assert {k: pending[k] for k in VALIDATE_PROGRAM} == VALIDATE_PROGRAM
    assert [(f["id"], f["label"]) for f in pending["fields"]] == [
        ("note", "Ce qu'il faut revoir (pour une révision)")
    ]
    ready = (await c.events("artifact.ready"))[0]
    pid = ready["artifact_id"]
    assert ready == {
        "artifact_id": pid,
        "kind": "program",
        "title": "Parcours IA",
        "url": f"/apprendre/programme/{pid}",
    }
    said = await c.events("agent.message")
    assert "2 semaine(s)" in said[-1]["text"] and "85 %" in said[-1]["text"]
    prompt = c.prompt_of_call(1)
    for expected in (
        "714 min",
        "au moins 428 min",
        "Parcours pratique",
        "Le soir surtout",
        "en français",
    ):
        assert expected in prompt
    assert 'source="proposition 1"' in prompt and 'source="compte rendu du Scribe"' in prompt
    assert "MÉLANGER" not in prompt and len(c.plan_prompts()) == 1  # conforme du premier coup
    saved = c.store.drafts[0]
    assert str(saved.start_date) == "2026-11-16" and saved.reason == "Première version du Stratège"


async def test_mix_of_two_proposals_is_one_program(make_builder_runner: MakeBuilder) -> None:
    c = await make_builder_runner(mix=True)
    await c.wait_question()
    prompt = c.prompt_of_call(1)
    assert "MÉLANGER" in prompt and "Parcours pratique" in prompt and "Nom : Socle" in prompt


async def test_draft_over_budget_is_asked_again_with_problems(
    make_builder_runner: MakeBuilder,
) -> None:
    c = await make_builder_runner(_models(OVER))
    await c.wait_question()
    assert "714 au plus" in c.prompt_of_call(2)
    assert "714 au plus" not in c.prompt_of_call(1)
    assert len(c.plan_prompts()) == 2 and len(c.store.drafts) == 1
    assert [w.theme for w in c.store.drafts[0].draft.weeks] == ["Bases", "Projet"]  # le corrigé


async def test_third_bad_draft_is_packed_by_rules(make_builder_runner: MakeBuilder) -> None:
    c = await make_builder_runner(_models(OVER, OVER, OVER))
    await c.wait_question()
    assert len(c.plan_prompts()) == 3  # une demande, deux re-demandes, puis le code range
    scheduled = c.store.drafts[0].plan
    assert len(scheduled.weeks) > 1 and scheduled.moved_tasks > 0
    assert all(w.load_minutes <= 714 for w in scheduled.weeks)
    for each in scheduled.weeks:
        kinds = [t.type for t in each.tasks]
        assert "pratiquer" in kinds and kinds[-1] == "quiz"
    said = await c.events("agent.message")
    assert "reportée(s)" in said[-1]["text"]


async def test_known_skill_reduced_to_review(make_builder_runner: MakeBuilder) -> None:
    pandas = module(
        "Manipuler pandas",
        [task("Lire la documentation de pandas", minutes=60), task("Pratiquer", "pratiquer", 60)],
        ["pandas"],
    )
    charts = module("Tracer des graphiques", [task("Lire le guide", minutes=45)], ["matplotlib"])
    rest = module("Nettoyer", [task("Pratiquer le nettoyage", "pratiquer"), task("Faire", "quiz")])
    draft = plan([week("Données", [pandas, charts, rest])]).model_dump_json()
    known = {"pandas": "declare", "matplotlib": "valide"}
    c = await make_builder_runner(_models(draft), prepare=lambda s: setattr(s, "known", known))
    await c.wait_question()
    assert "pandas (déclaré)" in c.prompt_of_call(1)
    assert "ne replanifie pas ce qui est acquis" in c.prompt_of_call(1)
    tasks = [t for w in c.store.drafts[0].plan.weeks for t in w.tasks]
    review = [t for t in tasks if t.already_known]
    assert [(t.title, t.minutes) for t in review] == [("Réviser : Manipuler pandas", 20)]
    assert not any("pandas" in t.title for t in tasks if not t.already_known)
    assert c.store.drafts[0].plan.skipped_modules == ["Tracer des graphiques"]
    said = await c.events("agent.message")
    assert "Déjà acquis, sautés : Tracer des graphiques." in said[-1]["text"]


async def test_revise_note_produces_a_new_version(make_builder_runner: MakeBuilder) -> None:
    c = await make_builder_runner()
    first = await c.wait_question()
    pid = await _program_id(c)
    c.store.plans[pid] += "\n- 18/11 : Tâche déplacée par January (lire, 30 min)"
    await c.resume({"action": "revise", "note": "Moins de vidéos"})
    second = await c.wait_question(after=first)
    assert [d.revision for d in c.store.drafts] == [0, 1]
    last = c.prompt_of_last_plan()
    assert "Moins de vidéos" in last
    assert "Tâche déplacée par January" in last and "Révision n° 1" in last
    assert 'source="note de révision de January"' in last and 'source="plan courant"' in last
    assert c.store.contexts == [None, pid]  # le plan courant est relu en base
    assert c.store.drafts[1].reason == "Révision 1 : Moins de vidéos"
    await c.resume({"answers": {"note": "Plus de pratique"}})  # le champ seul : une révision
    await c.wait_question(after=second)
    assert [d.revision for d in c.store.drafts] == [0, 1, 2]
    assert "Plus de pratique" in c.prompt_of_last_plan()
    assert {r["artifact_id"] for r in await c.events("artifact.ready")} == {pid}
    await c.resume("validate")
    done = await c.wait_status("completed")
    assert c.store.validated == [pid] and done.pending_interrupt is None
    assert (await c.events("run.completed"))[0]["summary"] == "Programme validé : « Parcours IA »."


async def test_validate_calls_store_once_even_after_replay(
    make_builder_runner: MakeBuilder,
) -> None:
    # Arrêt du back juste après `validate` : `finalize` rejoué revalide sans effet de plus.
    first = await make_builder_runner()
    await first.wait_question()
    pid = await _program_id(first)
    first.store.block_after_validate = True
    await first.resume({"action": "validate"})
    await wait_until(lambda: first.store.validate_calls == 1)
    await first.runner.shutdown()
    first.store.block_after_validate = False
    second = await make_builder_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert second.store.validate_calls == 2 and second.store.validated == [pid]
    assert second.plan_prompts() == []  # rien avant `finalize` n'est rejoué
    assert len(second.store.drafts) == 1


async def test_save_replayed_writes_one_version(make_builder_runner: MakeBuilder) -> None:
    # Arrêt du back juste après `save_draft` : `save` rejoué relit la même version, sans
    # rappeler le Stratège ni écrire une seconde version.
    first = await make_builder_runner(prepare=lambda s: setattr(s, "block_after_save", True))
    await wait_until(lambda: first.store.save_calls == 1)
    await first.runner.shutdown()
    first.store.block_after_save = False
    second = await make_builder_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_question()
    assert second.store.save_calls == 2 and len(second.store.drafts) == 1
    assert second.plan_prompts() == []
    assert len(await second.events("artifact.ready")) == 1


async def test_invalid_answer_asks_again(make_builder_runner: MakeBuilder) -> None:
    c = await make_builder_runner()
    pending = await c.wait_question()
    for invalid in ("go", {"action": "publish"}, {"answers": {"autre": "x"}}, 42):
        await c.resume(invalid)
        again = await c.wait_question(after=pending)
        assert {k: again[k] for k in VALIDATE_PROGRAM} == VALIDATE_PROGRAM
        pending = again
    assert len(c.store.drafts) == 1 and c.store.validated == []
    await c.resume({"action": "validate", "note": "ignorée"})
    await c.wait_status("completed")
    assert len(c.store.validated) == 1 and len(c.plan_prompts()) == 1


async def test_planning_impossible_fails_readably(make_builder_runner: MakeBuilder) -> None:
    tiny = Budget(5, 5)  # 30 min par semaine : ni pratique ni quiz n'y tiennent
    c = await make_builder_runner(prepare=lambda s: setattr(s, "budget", tiny))
    row = await c.wait_status("failed")
    assert row.error is not None and row.error["code"] == "planning_impossible"
    failed = await c.events("run.failed")
    assert failed[-1]["message"].startswith("Budget hebdomadaire trop faible")
    assert c.store.drafts == [] and await c.events("artifact.ready") == []


async def test_logs_never_contain_plan_content(
    make_builder_runner: MakeBuilder, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    secret = plan([full_week("Thème secret", [120] * 8)], title="Titre secret")
    c = await make_builder_runner(_models(*[secret.model_dump_json()] * 3))
    await c.wait_question()
    await c.resume({"action": "revise", "note": "Note privée de January"})
    await c.wait_question(after=c.pending)
    await c.resume("validate")
    await c.wait_status("completed")
    for text in ("Titre secret", "Thème secret", "Note privée", "Parcours pratique"):
        assert text not in caplog.text
    assert c.sid in caplog.text  # journaux par identifiants


async def test_input_takes_one_or_two_proposals(make_builder_runner: MakeBuilder) -> None:
    c = await make_builder_runner()
    body = {"goal_id": GOAL_ID, "proposal_ids": ["a", "b", "c"]}
    with pytest.raises(AppError) as error:
        await c.runner.start(c.user_id, "program_builder", body)
    assert error.value.code == "invalid_input" and error.value.details == {
        "fields": ["proposal_ids"]
    }


def test_parse_validation() -> None:
    validate = ValidationAnswer(action="validate")
    assert parse_validation("validate") == validate
    assert parse_validation({"action": "validate", "note": "x"}) == validate
    assert parse_validation({"action": "revise", "note": "  Moins  "}) == ValidationAnswer(
        action="revise", note="Moins"
    )
    assert parse_validation({"answers": {"note": "Plus court"}}) == ValidationAnswer(
        action="revise", note="Plus court"
    )
    long = parse_validation({"action": "revise", "note": "a" * 3000})
    assert long is not None and len(long.note) == 2000  # coupée, jamais perdue
    for invalid in ("go", None, 3, {"action": "x"}, {"answers": {}}, {"answers": "x"}):
        assert parse_validation(invalid) is None
    assert json.loads(ValidationAnswer(action="revise").model_dump_json())["note"] == ""
