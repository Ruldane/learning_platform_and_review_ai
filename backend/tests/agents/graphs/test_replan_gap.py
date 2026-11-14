"""Déclencheur `gap` du parcours `replan` (« Ajouter au planning », D123, preflight G12) : sans
question d'option, ajouts seuls dans le module « Compétences des offres » (`m0`), chacun nommant
une compétence de la liste ; un retrait proposé n'est jamais appliqué ; la proposition reste
soumise à January."""

import logging
from typing import Any

import pytest

from app.agents.nodes.strategist.replan_steps import EMPTY_TEXT, GAP_EMPTY_TEXT, REPLAN_REQUEST
from app.core.errors import AppError
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.replan_support import MakeReplan, reply
from tests.support.replan import GAP_MODULE_ID, PROGRAM_ID, replan_context

GAP = {"program_id": PROGRAM_ID, "trigger": "gap", "skills": ["LangGraph", "Évaluation de RAG"]}


def _task(
    title: str, module: str = "m0", criterion: str = "Un résultat montrable"
) -> dict[str, Any]:
    return {
        "module": module,
        "title": title,
        "type": "pratiquer",
        "minutes": 45,
        "done_criterion": criterion,
    }


def _models(*replies: str) -> CouncilModels:
    models = CouncilModels()
    models.when("strategist", REPLAN_REQUEST, *replies)
    return models


async def test_gap_trigger_adds_tasks_for_given_skills(make_replan_runner: MakeReplan) -> None:
    adds = [_task("Pratiquer LangGraph sur un agent"), _task("Lire", criterion="Évaluation de RAG")]
    proposal = reply("J'ajoute deux tâches en fin de programme.", add=adds)
    run = await make_replan_runner(_models(proposal), body=GAP)
    await run.wait_question()  # directement l'acceptation : aucune question d'option
    assert await run.kinds() == ["accept_replan"]
    call = run.store.previews[0]
    assert call.option is None and call.draft.drop == []
    assert [t.title for t in call.draft.add] == ["Pratiquer LangGraph sur un agent", "Lire"]
    assert "LangGraph" in call.draft.add[0].title and {t.module for t in call.draft.add} == {"m0"}
    assert call.refs["m0"] == GAP_MODULE_ID and call.reason == "Compétences des offres"
    assert run.store.context_calls[0]["skills"] == ["LangGraph", "Évaluation de RAG"]
    prompt = run.prompts()[0]
    assert 'source="competences des offres"' in prompt and "- Évaluation de RAG" in prompt
    assert "m0 : Compétences des offres" in prompt
    assert '"add"' in prompt and '"drop"' not in prompt  # ajouts seuls (ReplanAdds)
    await run.resume("accept")
    await run.wait_status("completed")
    assert run.store.applied == [call.revision + 2]


async def test_gap_trigger_ignores_drops(make_replan_runner: MakeReplan) -> None:
    # Preflight G12 : le schéma `ReplanAdds` n'a pas de `drop` ; un retrait scripté est ignoré,
    # jamais appliqué, et ne coûte aucune re-demande.
    proposal = reply("Je retire et j'ajoute.", drop=["t5"], add=[_task("Pratiquer LangGraph")])
    run = await make_replan_runner(_models(proposal), body=GAP)
    await run.wait_question()
    call = run.store.previews[0]
    assert call.draft.drop == [] and [t.title for t in call.draft.add] == ["Pratiquer LangGraph"]
    assert len(run.prompts()) == 1


async def test_gap_task_in_another_module_goes_to_m0(make_replan_runner: MakeReplan) -> None:
    proposal = reply("J'ajoute.", add=[_task("Pratiquer LangGraph", module="m2")])
    run = await make_replan_runner(_models(proposal), body=GAP)
    await run.wait_question()
    assert [t.module for t in run.store.previews[0].draft.add] == ["m0"]


async def test_gap_task_without_skill_is_asked_again_then_removed(
    make_replan_runner: MakeReplan,
) -> None:
    vague = reply("J'ajoute.", add=[_task("Pratiquer LangGraph"), _task("Lire un article")])
    run = await make_replan_runner(_models(vague, vague), body=GAP)
    await run.wait_question()
    prompts = run.prompts()
    assert len(prompts) == 2
    asked = prompts[1].split(REPLAN_REQUEST)[-1]
    assert "n° 2" in asked and "Évaluation de RAG" not in asked  # des rangs, jamais l'offre
    assert [t.title for t in run.store.previews[0].draft.add] == ["Pratiquer LangGraph"]


async def test_gap_task_fixed_after_asking_is_kept(make_replan_runner: MakeReplan) -> None:
    vague = reply("J'ajoute.", add=[_task("Lire un article")])
    fixed = reply("J'ajoute.", add=[_task("Lire un article sur l'évaluation de RAG")])
    run = await make_replan_runner(_models(vague, fixed), body=GAP)
    await run.wait_question()
    titles = [t.title for t in run.store.previews[0].draft.add]
    assert titles == ["Lire un article sur l'évaluation de RAG"]


async def test_gap_needs_skills_and_only_gap_takes_them(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(body=GAP)
    message = {"program_id": PROGRAM_ID, "trigger": "message", "skills": ["LangGraph"]}
    for body in (
        {"program_id": PROGRAM_ID, "trigger": "gap"},
        GAP | {"skills": [""]},
        GAP | {"skills": [f"C{n}" for n in range(11)]},
        message,
    ):
        with pytest.raises(AppError) as error:
            await run.runner.start(run.user_id, "replan", body)
        assert error.value.code == "invalid_input"


async def test_gap_logs_carry_ids_only(
    make_replan_runner: MakeReplan, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    vague = reply("Résumé secret du Stratège.", add=[_task("Lire un article secret")])
    run = await make_replan_runner(_models(vague, vague), plan=replan_context(), body=GAP)
    await run.wait_status("completed")  # tout ajout retiré : rien à changer
    for text in ("Résumé secret", "article secret", "LangGraph", "Évaluation de RAG"):
        assert text not in caplog.text
    assert run.sid in caplog.text


async def test_gap_with_nothing_added_says_what_happened(make_replan_runner: MakeReplan) -> None:
    """Deux réponses qui n'ajoutent rien d'utile : jamais « ton plan tient tel quel » juste après
    « Ajouter au planning » (revue 6.7, M7)."""
    vague = reply("J'ajoute.", add=[_task("Lire un article")])  # aucune compétence nommée
    run = await make_replan_runner(_models(vague, vague), body=GAP)
    done = await run.wait_status("completed")
    assert done.pending_interrupt is None
    [summary] = [e["summary"] for e in await run.events("run.completed")]
    assert summary == GAP_EMPTY_TEXT and EMPTY_TEXT not in summary
    assert "Ajouter au planning" in summary and "n'a pas changé" in summary
    assert await run.said() == [GAP_EMPTY_TEXT]
