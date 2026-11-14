"""Port des gabarits (`AgentCvTemplateStore`, D126) : mise en page extraite une seule fois (à la
création), `prepare` relu sans rien refaire, passes rendues une fois puis relues (`render_pass`,
`read_pass`), polices téléchargées une fois et réutilisées d'un gabarit à l'autre, repli sur
Liberation Sans, premier gabarit prêt actif, contenu de démonstration tiré du profil validé."""

import pytest

from app.core.errors import AppError
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.templates_store import AgentCvTemplateStore
from app.providers.fonts.fake import FakeFontSource
from scripts.sample_cv import CV_FACTS, SampleCv, make_cv_pdf
from tests.features.cv.templates_support import (
    CountingLayout,
    capture,
    end_sessions,
    liberation_spec,
    template_row,
)
from tests.features.cv.test_profile_store import ME, add_version
from tests.support.cv_template import content as cv_content
from tests.support.cv_templates import similarity
from tests.support.text_renderer import TextHtmlRenderer

PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def store_real(cv_runtime: CvRuntime) -> AgentCvTemplateStore:
    return AgentCvTemplateStore(cv_runtime)


def fake_fonts(rt: CvRuntime) -> FakeFontSource:
    assert isinstance(rt.fonts, FakeFontSource)
    return rt.fonts


async def test_store_prepare_is_idempotent(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    counting = CountingLayout(cv_runtime.layout)
    cv_runtime.layout = counting
    template_id = await capture(cv_runtime)
    assert counting.calls == 1  # extraite à la création, jamais par `prepare`
    first = await store_real.prepare(ME, template_id)
    again = await store_real.prepare(ME, template_id)
    assert first == again and counting.calls == 1
    assert fake_fonts(cv_runtime).calls == [("Liberation Sans", (400, 700))]  # une seule fois
    assert first.page_count == 1 and first.page_size == (595.0, 842.0) and first.selectable
    assert len(first.pages_png) == 1 and first.pages_png[0].startswith(PNG)
    assert first.available_fonts == ["Liberation Sans", "Liberation Serif"]
    assert CV_FACTS["name"] in first.original_text and CV_FACTS["role_1"] in first.original_text
    assert "Helvetica" not in first.blocks_summary  # familles libres seulement
    assert "| Liberation Sans | 22 | " in first.blocks_summary
    assert [font.family for font in first.fonts] == ["Liberation Sans", "Liberation Sans"]


async def test_prepare_unknown_template_is_404(store_real: AgentCvTemplateStore) -> None:
    with pytest.raises(AppError) as caught:
        await store_real.prepare(ME, "inconnu")
    assert caught.value.status_code == 404


async def test_render_pass_stored_and_reused(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    renderer = cv_runtime.html_pdf
    assert isinstance(renderer, TextHtmlRenderer)
    template_id = await capture(cv_runtime)
    await store_real.prepare(ME, template_id)
    done = await store_real.render_pass(ME, template_id, 1, liberation_spec(), cv_content())
    assert 0 <= done.score <= 100 and done.similarity.pages_original == 1
    assert len(done.render_png) == 1 and done.render_png[0].startswith(PNG)
    assert len(renderer.documents) == 1
    assert {"liberation-sans-400.ttf", "liberation-sans-700.ttf"} <= set(
        renderer.documents[0].assets
    )
    again = await store_real.render_pass(ME, template_id, 1, liberation_spec(), cv_content())
    assert again == done and len(renderer.documents) == 1  # relue, jamais rendue deux fois
    assert await store_real.read_pass(ME, template_id, 1) == done
    with pytest.raises(AppError) as caught:
        await store_real.read_pass(ME, template_id, 2)
    assert caught.value.code == "template_pass_not_found"
    row = await template_row(cv_runtime, template_id)
    assert (row.passes, row.score, len(row.render_pages)) == (1, done.score, 1)
    assert row.html and "@page" in (row.css or "") and row.spec is not None
    assert row.score_detail is not None and row.score_detail["score"] == done.score


async def test_font_unavailable_falls_back(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    fake_fonts(cv_runtime).unavailable.add("Carlito")
    template_id = await capture(cv_runtime, make_cv_pdf(SampleCv(font="Calibri")))
    created = await template_row(cv_runtime, template_id)
    assert created.font_gaps == [
        "La police du texte et des titres n'est pas libre : remplacée par Carlito, très proche."
    ]
    view = await store_real.prepare(ME, template_id)
    assert "Carlito" not in view.available_fonts
    # Revue 6.10, M1 : rien d'indisponible n'est proposé au Maquettiste (vue ni blocs résumés).
    assert {font.family for font in view.fonts} <= set(view.available_fonts)
    assert "Carlito" not in view.blocks_summary and "| Liberation Sans |" in view.blocks_summary
    row = await template_row(cv_runtime, template_id)
    assert {(use["family"], use["substitute"]) for use in row.fonts} == {("Liberation Sans", True)}
    assert row.font_gaps == [
        "La police du texte et des titres n'a pas pu être chargée : remplacée par Liberation Sans."
    ]
    assert not any("Calibri" in gap for gap in row.font_gaps)


async def test_failed_template_refuses_passes_and_ready(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    """Revue 6.10, M2 : un gabarit en échec est figé."""
    template_id = await capture(cv_runtime)
    await store_real.prepare(ME, template_id)
    await store_real.finish(ME, template_id, "failed", "Capture abandonnée.")
    renderer = cv_runtime.html_pdf
    assert isinstance(renderer, TextHtmlRenderer)
    with pytest.raises(AppError) as caught:
        await store_real.render_pass(ME, template_id, 1, liberation_spec(), cv_content())
    assert (caught.value.code, caught.value.status_code) == ("template_not_capturing", 409)
    assert renderer.documents == []
    with pytest.raises(AppError) as caught:
        await store_real.finish(ME, template_id, "ready", None)
    assert caught.value.code == "template_not_capturing"
    await store_real.finish(ME, template_id, "failed", "Autre raison.")  # idempotent
    row = await template_row(cv_runtime, template_id)
    assert (row.status, row.failure_reason, row.pass_log) == ("failed", "Capture abandonnée.", [])


async def test_best_pass_is_the_one_kept(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scores 69, 78, 69 : le gabarit garde la passe 2 ; à égalité, la plus récente ; une passe
    d'ajustement remplace toujours. Toutes restent dans le journal des passes."""
    scores = iter([69, 78, 69, 78, 50])
    monkeypatch.setattr(
        "app.features.cv.service.templates_store.similarity",
        lambda original, render: similarity(next(scores)),
    )
    template_id = await capture(cv_runtime)
    await store_real.prepare(ME, template_id)
    seen: list[tuple[int | None, str | None]] = []
    for pass_no, mark in ((1, "#aa0000"), (2, "#bb0000"), (3, "#cc0000"), (4, "#dd0000")):
        spec = liberation_spec().model_copy(update={"accent": mark})
        await store_real.render_pass(ME, template_id, pass_no, spec, cv_content())
        row = await template_row(cv_runtime, template_id)
        seen.append((row.score, (row.spec or {}).get("accent")))
    assert seen == [
        (69, "#aa0000"),
        (78, "#bb0000"),
        (78, "#bb0000"),
        (78, "#dd0000"),
    ]  # 4 : égalité, la plus récente
    spec = liberation_spec().model_copy(update={"accent": "#ee0000"})
    await store_real.render_pass(ME, template_id, 5, spec, cv_content(), adjusted=True)
    row = await template_row(cv_runtime, template_id)
    assert (row.score, (row.spec or {}).get("accent"), len(row.pass_log)) == (50, "#ee0000", 5)
    assert row.score_detail is not None and row.score_detail["score"] == 50


async def test_fonts_downloaded_once_for_all_templates(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    pdf = make_cv_pdf(SampleCv(font="Calibri"))
    first = await capture(cv_runtime, pdf)
    await store_real.prepare(ME, first)
    await store_real.finish(ME, first, "failed", "Capture abandonnée.")
    await end_sessions(cv_runtime)
    second = await capture(cv_runtime, pdf)
    view = await store_real.prepare(ME, second)
    assert fake_fonts(cv_runtime).calls == [("Carlito", (400, 700))]
    assert view.available_fonts[0] == "Carlito"
    spec = liberation_spec()
    carlito = spec.model_copy(
        update={"fonts": spec.fonts.model_copy(update={"body": "Carlito", "heading": "Carlito"})}
    )
    await store_real.render_pass(ME, second, 1, carlito, cv_content())
    renderer = cv_runtime.html_pdf
    assert isinstance(renderer, TextHtmlRenderer)
    assert {"carlito-400.ttf", "carlito-700.ttf"} <= set(renderer.documents[-1].assets)


async def test_first_ready_template_becomes_active(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    first = await capture(cv_runtime)
    await store_real.finish(ME, first, "ready", None)
    await end_sessions(cv_runtime)
    second = await capture(cv_runtime)
    await store_real.finish(ME, second, "ready", None)
    await store_real.finish(ME, second, "failed", "Capture abandonnée.")  # prêt : ne change plus
    rows = [await template_row(cv_runtime, tid) for tid in (first, second)]
    assert [(row.status, row.active) for row in rows] == [("ready", True), ("ready", False)]


async def test_finish_failed_keeps_the_reason(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    template_id = await capture(cv_runtime)
    await store_real.finish(ME, template_id, "failed", "Capture abandonnée.")
    await store_real.finish(ME, template_id, "failed", "Capture abandonnée.")
    row = await template_row(cv_runtime, template_id)
    assert (row.status, row.failure_reason, row.active) == ("failed", "Capture abandonnée.", False)


async def test_sample_fallback_from_the_validated_profile(
    cv_runtime: CvRuntime, store_real: AgentCvTemplateStore
) -> None:
    assert await store_real.sample_fallback(ME) is None
    await add_version(cv_runtime.session_factory, 1)
    sample = await store_real.sample_fallback(ME)
    assert sample is not None and sample.name == CV_FACTS["name"]
    keys = [section.key for section in sample.sections]
    assert "experience" in keys
    assert all(not line.fact_ids for s in sample.sections for line in s.items)
