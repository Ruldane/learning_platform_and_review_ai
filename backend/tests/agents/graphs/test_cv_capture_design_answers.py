"""Parcours `cv_capture` en mode `design` (D125) : la question `cv_template` et ses réponses.
Valider ou recommencer termine le gabarit ; ajuster lance une correction avec la consigne (cinq au
plus) ; l'interruption est seule dans son nœud ; une correction sans sortie valable garde la
dernière passe et repose la question (revue 6.9, I2)."""

import inspect

from app.agents.graphs.cv_capture_design import ask_validate, kept_score_of
from app.agents.nodes.designer import FIX_REQUEST
from app.agents.nodes.designer_steps import MAX_ADJUSTMENTS
from tests.agents.graphs.design_support import INSTRUCTION, MakeDesign, designer, values
from tests.support.cv_template import spec as cv_spec
from tests.support.cv_templates import FakeCvTemplateStore, spec_reply

NOT_JSON = "Voici la description corrigée, sans JSON."
STALLED = "Je n'ai pas su corriger la description : le modèle reste tel quel."


async def test_validate_finishes_ready(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    run = await design_runner()
    await run.question()
    await run.answer("validate")
    await run.wait_status("completed")
    assert design_store.finished == {"t1": ("ready", None)}
    [artifact] = await run.events("artifact.ready")
    assert artifact == {
        "artifact_id": "modele-t1",
        "kind": "cv_template",
        "title": "Modèle de CV",
        "url": "/carriere/cv/modeles/t1",
    }
    [done] = await run.events("run.completed")
    assert done["summary"] == "Modèle de CV prêt : il ressemble à ton CV à 90 %."


async def test_restart_finishes_failed(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    run = await design_runner()
    await run.question()
    await run.answer("restart")
    await run.wait_status("completed")
    assert design_store.finished == {"t1": ("failed", "Capture abandonnée.")}
    assert await run.events("artifact.ready") == []


async def test_adjust_runs_fix_with_instruction(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.scores = [90, 80]
    run = await design_runner()
    await run.question()
    await run.answer({"answers": {"instruction": f"  {INSTRUCTION}  "}})
    question = await run.question()  # passe d'un ajustement : question aussitôt, même sous 85
    assert design_store.rendered == [1, 2]
    assert design_store.kept == 2  # l'ajustement remplace la passe gardée, même moins bien noté
    assert question["question"].startswith("Le modèle ressemble à ton CV à 80 %.")
    [fix] = run.prompts(FIX_REQUEST)
    assert '<<<CONTENU_NON_FIABLE source="consigne de January">>>' in fix
    assert INSTRUCTION in fix and "Écarts mesurés" not in fix  # 90 % : pas d'écarts décrits
    assert design_store.spec_of(2) == cv_spec()


async def test_adjustments_capped_at_five(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    run = await design_runner()
    await run.question()
    for n in range(MAX_ADJUSTMENTS):
        await run.answer({"action": "adjust", "instruction": f"{INSTRUCTION} ({n})"})
        question = await run.question()
    assert design_store.rendered == [1, 2, 3, 4, 5, 6]
    assert values(question) == ["validate", "restart"] and question["fields"] == []
    assert "5 ajustements possibles" in question["question"]
    await run.answer({"answers": {"instruction": INSTRUCTION}})
    again = await run.question()  # sixième ajustement refusé : même question, aucun rendu
    assert again["question"] == question["question"] and design_store.rendered[-1] == 6
    await run.answer("validate")
    await run.wait_status("completed")
    assert design_store.finished["t1"] == ("ready", None)


async def test_interrupt_node_has_no_write(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    assert list(inspect.signature(ask_validate).parameters) == ["state"]  # ni port ni modèle
    run = await design_runner()
    first = await run.question()
    calls, model_calls = list(design_store.calls), len(run.models.calls)
    await run.answer("adjust")  # sans consigne : la question est reposée
    again = await run.question()
    assert again["interrupt_id"] != first["interrupt_id"]
    assert design_store.calls == calls and len(run.models.calls) == model_calls


async def test_fix_with_invalid_structured_output_keeps_the_last_pass(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    """GLM rend trois fois un JSON illisible pendant une correction : la passe rendue reste, la
    question est posée (revue 6.9, I2)."""
    design_store.scores = [60]
    run = await design_runner(designer(fix=[NOT_JSON] * 3))
    question = await run.question()
    assert design_store.rendered == [1] and len(run.prompts(FIX_REQUEST)) == 3
    assert question["question"].startswith("Le modèle ressemble à ton CV à 60 %.")
    assert (await run.said())[-1] == STALLED and design_store.finished == {}


async def test_stalled_adjustment_is_consumed_then_validate_keeps_the_last_pass(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    run = await design_runner(designer(fix=[NOT_JSON] * 3))
    first = await run.question()
    await run.answer({"answers": {"instruction": INSTRUCTION}})
    again = await run.question()  # même score, aucun rendu, l'ajustement est compté
    assert again["question"] == first["question"] and design_store.rendered == [1]
    assert (await run.said())[-1] == STALLED
    for n in range(MAX_ADJUSTMENTS - 1):
        await run.answer({"answers": {"instruction": f"{INSTRUCTION} ({n})"}})
        await run.question()
    assert values(run.pending or {}) == ["validate", "restart"]  # 1 calé + 4 rendus = 5
    await run.answer("validate")
    await run.wait_status("completed")
    assert design_store.finished == {"t1": ("ready", None)}
    assert design_store.rendered == [1, 2, 3, 4, 5] and design_store.spec_of(5) == cv_spec()


async def test_adjust_after_a_worse_last_pass_starts_from_the_kept_pass(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    """Scores 69, 78, 69 : la passe 2 est gardée ; « Ajuster » repart d'elle (sa description, son
    score, ses images), jamais de la passe 3 (revue 6.10, N1)."""
    design_store.scores = [69, 78, 69, 80]
    fixes = [
        spec_reply(accent="#a11111"),
        spec_reply(accent="#a22222"),
        spec_reply(accent="#a33333"),
    ]
    run = await design_runner(designer(fix=fixes))
    await run.question()
    assert design_store.kept == 2
    await run.answer({"answers": {"instruction": INSTRUCTION}})
    await run.question()
    third = run.prompts(FIX_REQUEST)[2]
    assert "#a11111" in third and "#a22222" not in third  # la description de la passe 2
    assert "Passe 2 : ressemblance de 78 %." in third
    assert design_store.passes[4][0].accent == "#a33333" and design_store.kept == 4


async def test_ask_validate_reads_an_older_checkpoint_without_kept_score() -> None:
    """Un checkpoint d'avant `kept_score` montre le score de la dernière passe (revue 6.10, N2)."""
    assert kept_score_of({"score": 72}) == 72
    assert kept_score_of({"score": 72, "kept_score": 78}) == 78
    assert kept_score_of({}) == 0
