"""Parcours `cv_capture` en mode `design` (D125) : le Maquettiste recopie le contenu, décrit le
design et le corrige d'après le score ; trois passes automatiques au plus, puis la question
`cv_template` quel que soit le score ; une passe n'est jamais rendue deux fois. Les réponses à la
question : `test_cv_capture_design_answers.py`."""

import base64
import logging

import pytest

from app.agents.graphs.cv_capture import CvCaptureInput
from app.agents.nodes.designer import DRAFT_REQUEST, FIX_REQUEST, NO_SAMPLE, NO_SPEC
from app.agents.tools.cv_schema import CvContent
from scripts.sample_cv import CV_FACTS
from tests.agents.graphs.design_support import OPTIONS, MakeDesign, bad_font_spec, designer, values
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.cv_templates import (
    ORIGINAL_PNG,
    FakeCvTemplateStore,
    profile_sample,
    render_png,
    sample_dict,
    sample_reply,
)


async def test_design_capture_reaches_target_in_two_passes(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.scores = [72, 88]
    run = await design_runner()
    question = await run.question()
    assert design_store.rendered == [1, 2] and question["kind"] == "cv_template"
    assert question["question"] == "Le modèle ressemble à ton CV à 88 %. Tu valides ?"
    assert values(question) == OPTIONS
    assert question["fields"] == [
        {
            "id": "instruction",
            "label": "Ce qu'il faut changer",
            "required": False,
            "max_length": 500,
        }
    ]
    [fix] = run.prompts(FIX_REQUEST)
    assert "Passe 1 : ressemblance de 72 %." in fix and "Écarts mesurés" in fix
    assert await run.said() == [
        "Passe 1 : le rendu ressemble à ton CV à 72 %.",
        "Passe 2 : le rendu ressemble à ton CV à 88 %.",
    ]


async def test_three_passes_at_most(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.scores = [60, 65, 70]
    run = await design_runner()
    question = await run.question()
    assert design_store.rendered == [1, 2, 3] and len(run.prompts(FIX_REQUEST)) == 2
    assert question["question"].startswith("Le modèle ressemble à ton CV à 70 %.")
    assert design_store.finished == {}  # jamais d'échec silencieux : la question est posée


async def test_best_pass_is_kept_and_its_score_shown(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    """Scores 69, 78, 69 : le gabarit garde la passe 2, la question et le message final disent
    78 %, jamais 69 % (essai réel de 6.11)."""
    design_store.scores = [69, 78, 69]
    run = await design_runner()
    question = await run.question()
    assert design_store.rendered == [1, 2, 3] and design_store.kept == 2
    assert question["question"].startswith("Le modèle ressemble à ton CV à 78 %.")
    assert (await run.said())[
        -1
    ] == "Passe 3 : le rendu ressemble à ton CV à 69 %. Je garde la passe 2 (78 %)."
    await run.answer("validate")
    await run.wait_status("completed")
    assert design_store.finished_pass == {"t1": 2}
    [done] = await run.events("run.completed")
    assert done["summary"] == "Modèle de CV prêt : il ressemble à ton CV à 78 %."


async def test_tie_keeps_the_later_pass(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.scores = [70, 70, 60]
    run = await design_runner()
    question = await run.question()
    assert design_store.kept == 2
    assert question["question"].startswith("Le modèle ressemble à ton CV à 70 %.")


async def test_replay_between_passes_renders_once(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    """Le back s'arrête après le rendu de la passe 2, pendant la correction qui suit (preflight
    G34 : on compte les appels au port, pas les rendus du faux)."""
    design_store.scores = [60, 70, 90]
    models = designer()
    models.block = lambda agent, prompt: FIX_REQUEST in prompt and "Passe 2 :" in prompt
    first = await design_runner(models)
    await wait_until(lambda: models.blocked == 1)
    assert design_store.render_calls == {1: 1, 2: 1}
    await first.runner.shutdown()
    models.block = None
    second = await design_runner(models, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    question = await second.question()
    assert design_store.render_calls == {1: 1, 2: 1, 3: 1}
    assert question["question"].startswith("Le modèle ressemble à ton CV à 90 %.")


async def test_sample_lines_are_verbatim(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    invented = "Pilotage d'une équipe de 12 personnes"
    sections = sample_dict()["sections"]
    sections[1]["entries"][0]["lines"].append({"text": invented})
    reply = sample_reply(sections=sections)
    run = await design_runner(designer(sample=[reply, reply]))
    await run.question()
    first, second = run.prompts("Recopie le contenu")[:2]
    assert "ne figurent pas tels quels" in second and invented in second
    assert "ne figurent pas tels quels" not in first
    _, content, _ = design_store.passes[1]
    lines = [line.text for line in content.sections[1].entries[0].lines]
    assert invented not in lines and len(lines) == 2
    assert content.sections[0].items[0].text.endswith("en agents conversationnels.")


async def test_scanned_cv_uses_profile_content(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.selectable, design_store.profile_content = False, profile_sample()
    run = await design_runner()
    await run.question()
    assert run.prompts("Recopie le contenu") == []
    _, content, _ = design_store.passes[1]
    assert content == profile_sample()


async def test_scanned_cv_without_profile_fails_readably(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.selectable = False
    run = await design_runner()
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "design_no_sample"
    assert row.error["message"] == NO_SAMPLE
    assert design_store.finished == {"t1": ("failed", NO_SAMPLE)}
    assert run.prompts() == [] and design_store.rendered == []


async def test_spec_with_unknown_font_is_reasked(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    run = await design_runner(designer(draft=[bad_font_spec()]))
    await run.question()
    first, second = run.prompts(DRAFT_REQUEST)[:2]
    assert "n'est pas disponible" in second and "n'est pas disponible" not in first
    assert design_store.spec_of(1).fonts.body == "Lato"


async def test_spec_still_invalid_after_two_reasks_fails_readably(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    run = await design_runner(designer(draft=[bad_font_spec()] * 3))
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "template_spec_invalid"
    assert row.error["message"] == NO_SPEC
    assert len(run.prompts(DRAFT_REQUEST)) == 3 and design_store.rendered == []
    assert design_store.finished == {"t1": ("failed", NO_SPEC)}


async def test_fix_without_valid_spec_keeps_current_and_asks(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.scores = [60]
    run = await design_runner(designer(fix=[bad_font_spec()] * 3))
    question = await run.question()
    assert design_store.rendered == [1] and len(run.prompts(FIX_REQUEST)) == 3
    assert question["question"].startswith("Le modèle ressemble à ton CV à 60 %.")
    assert "Je n'ai pas su corriger la description" in (await run.said())[-1]


async def test_images_are_sent_as_image_blocks(
    design_runner: MakeDesign, design_store: FakeCvTemplateStore
) -> None:
    design_store.scores = [72, 88]
    run = await design_runner()
    await run.question()

    def images(call: int) -> list[str]:
        return [
            block["base64"]
            for message in run.models.messages[call]
            if isinstance(message.content, list)
            for block in message.content
            if isinstance(block, dict) and block.get("type") == "image"
        ]

    def b64(png: bytes) -> str:
        return base64.b64encode(png).decode()

    assert [images(n) for n in range(3)] == [
        [b64(ORIGINAL_PNG)],  # contenu
        [b64(ORIGINAL_PNG)],  # design
        [b64(ORIGINAL_PNG), b64(render_png(1))],  # correction : original puis rendu
    ]
    block = next(
        b for b in run.models.messages[0][1].content if isinstance(b, dict) and "base64" in b
    )
    assert block["mime_type"] == "image/png"


async def test_design_never_logged(
    design_runner: MakeDesign, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    run = await design_runner(designer(draft=[bad_font_spec()]))
    await run.question()
    await run.answer("validate")
    await run.wait_status("completed")
    for secret in (CV_FACTS["name"], CV_FACTS["email"], CV_FACTS["role_1"], "Comic Sans"):
        assert secret not in caplog.text


def test_design_input() -> None:
    body = CvCaptureInput.model_validate({"mode": "design", "template_id": "t1"})
    assert body.document_ids == [] and body.template_id == "t1"
    with pytest.raises(ValueError):
        CvCaptureInput.model_validate({"mode": "design"})
    assert CvContent.model_validate(sample_dict()).name == CV_FACTS["name"]
