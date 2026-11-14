"""« Générer le PDF » (D130) : une version par clic, nom de fichier ASCII, décisions figées au
clic, une seule version en rendu, nombre de pages de l'original gardé par resserrement sinon
`pages_exceeded`, PDF fait des seuls faits du profil, indicateurs calculés sur le PDF rendu."""

import asyncio
from typing import Any

import httpx
from fastapi import FastAPI

from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.cv_schema import CvContent, MasterProfileData, facts_of
from app.core.errors import AppError
from app.db.models.career import CvVersion
from app.features.cv.service.runtime import CvRuntime
from tests.features.cv.reviews_support import (
    API,
    GAP_TEXT,
    SECRET_LINE,
    ResumeSpy,
    decide,
    mods,
    open_review,
    post_generate,
    set_session,
    version,
    wait_output,
)
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.cv_review import compose_profile
from tests.support.text_renderer import TextHtmlRenderer

FILENAME = "CV_Camille_Exemple_Societe_Fictive_AI_Product_Engineer.pdf"


def rt_of(app: FastAPI) -> CvRuntime:
    runtime: CvRuntime = app.state.career.cv
    return runtime


async def generate(client: httpx.AsyncClient, review_id: str, **body: Any) -> dict[str, Any]:
    r = await post_generate(client, review_id, **body)
    assert r.status_code == 202, r.text
    return await version(client, r.json()["version_id"])


async def pdf_text(app: FastAPI, client: httpx.AsyncClient, version_id: str) -> str:
    r = await client.get(f"{API}/cv/versions/{version_id}/pdf")
    assert r.status_code == 200
    layout = await rt_of(app).layout.extract_layout(r.content)
    return "\n".join(page.stream_text for page in layout.pages)


async def stored(app: FastAPI, version_id: str) -> CvVersion:
    async with app.state.session_factory() as db:
        row: CvVersion | None = await db.get(CvVersion, version_id)
    assert row is not None
    return row


async def test_generate_renders_version_with_filename(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, session_id = await open_review(client, app)
    v = await generate(client, review_id)
    assert v["filename"] == FILENAME and v["status"] == "ready"
    assert (v["number"], v["page_count"], v["original_page_count"]) == (1, 1, 1)
    [(sid, interrupt_id, value)] = resume_spy.calls
    assert (sid, interrupt_id, value) == (
        session_id,
        "i-1",
        {"choice": "pdf", "version_id": v["id"]},
    )
    second = await generate(client, review_id)
    assert second["number"] == 2  # une version par clic, numérotée par offre
    shown = (await client.get(f"{API}/cv/reviews/{review_id}")).json()
    assert [item["number"] for item in shown["versions"]] == [1, 2]


async def test_generate_keeps_original_page_count(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    fake_renderer.pages = (2, 1)  # 2 pages rendues pour 1 : un palier de resserrement suffit
    v = await generate(client, review_id)
    assert (v["status"], v["page_count"]) == ("ready", 1)
    assert len(fake_renderer.documents) == 2
    first, tightened = (doc.assets["cv.css"].decode() for doc in fake_renderer.documents)
    assert first != tightened  # le palier 1 resserre l'espace entre les blocs


async def test_pages_exceeded_then_allowed(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    fake_renderer.pages = (2,)
    v = await generate(client, review_id)
    assert (v["status"], v["page_count"], v["indicators"]) == ("pages_exceeded", 2, None)
    assert len(fake_renderer.documents) == 4  # rendu puis trois paliers
    missing = await client.get(f"{API}/cv/versions/{v['id']}/pdf")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "version_not_ready")
    allowed = await generate(client, review_id, allow_extra_pages=True)
    assert (allowed["status"], allowed["page_count"], allowed["allow_extra_pages"]) == (
        "ready",
        2,
        True,
    )
    assert len(fake_renderer.documents) == 5  # aucun resserrement quand la page de plus est permise


async def test_double_generate_is_409(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    resume_spy.render = False  # le rendu tourne encore
    a, b = await asyncio.gather(post_generate(client, review_id), post_generate(client, review_id))
    assert sorted([a.status_code, b.status_code]) == [202, 409]
    refused = b if b.status_code == 409 else a
    assert refused.json()["error"]["code"] == "generation_in_progress"
    versions = (await client.get(f"{API}/cv/versions")).json()
    assert len(versions) == 1 and versions[0]["status"] == "rendering"
    assert refused.json()["error"]["details"] == {"version_id": versions[0]["id"]}
    assert len(resume_spy.calls) == 1


async def test_generate_snapshots_decisions(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, session_id = await open_review(client, app)
    mid = (await mods(client, review_id))["a1"]["id"]
    await decide(client, mid, "accepted")
    resume_spy.render = False
    v1 = (await post_generate(client, review_id)).json()["version_id"]
    assert (await decide(client, mid, "refused")).json()["status"] == "refused"  # pendant le rendu
    await app.state.career.cv_review.render_version(app.state.local_user_id, v1)  # le parcours
    await wait_output(rt_of(app), session_id, "i-2")
    v2 = (await post_generate(client, review_id)).json()["version_id"]
    assert (await version(client, v1))["decisions"]["a1"] == "accepted"
    assert (await version(client, v2))["decisions"]["a1"] == "refused"
    first = CvContent.model_validate((await stored(app, v1)).content)
    texts = [line.text for s in first.sections for e in s.entries for line in e.lines]
    assert "Réduit les coûts de 30 % avec Python" in texts
    # le PDF rendu vient du contenu figé au clic, non des décisions prises pendant le rendu
    assert "avec Python" in " ".join((await pdf_text(app, client, v1)).split())


async def test_generate_needs_the_output_question(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, session_id = await open_review(client, app, proposed=False)
    r = await post_generate(client, review_id)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_not_waiting")
    await app.state.career.cv_review.save_proposals(
        app.state.local_user_id, session_id, review_id, [], [], ReviewReport()
    )
    await set_session(rt_of(app), session_id, "running")
    r = await post_generate(client, review_id)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_not_waiting")
    await wait_output(rt_of(app), session_id)
    resume_spy.error = AppError("stale_interrupt", "Question périmée.", 409)
    r = await post_generate(client, review_id)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_not_waiting")
    assert (await client.get(f"{API}/cv/versions")).json() == []  # reprise refusée : rien gardé


async def test_render_failure_is_failed_version(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    fake_renderer.failures = 1
    v = await generate(client, review_id)
    assert v["status"] == "failed"
    assert v["failure_reason"] == "Le PDF n'a pas pu être généré : réessaie dans un instant."
    assert (await generate(client, review_id))["status"] == "ready"


async def test_composed_pdf_has_only_profile_facts(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    by_ref = await mods(client, review_id)
    await client.patch(
        f"{API}/cv/reviews/{review_id}/modifications",
        json={"ids": [m["id"] for m in by_ref.values()], "status": "accepted"},
    )
    v = await generate(client, review_id)
    content = CvContent.model_validate((await stored(app, v["id"])).content)
    facts = facts_of(MasterProfileData.model_validate(compose_profile()))
    lines = [
        line
        for s in content.sections
        for line in [*s.items, *(x for e in s.entries for x in e.lines)]
    ]
    assert lines and all(line.fact_ids and set(line.fact_ids) <= set(facts) for line in lines)
    text = await pdf_text(app, client, v["id"])
    assert "Réduit les coûts de 30 % avec Python" in text and "Kubernetes" in text
    assert SECRET_LINE not in text  # « à confirmer » : jamais accepté en groupe
    assert GAP_TEXT not in text and "AWS" not in text  # parti vers l'écart
    assert "Adopté par 40 personnes" not in text  # retrait accepté


async def test_after_indicators_computed_on_rendered_pdf(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    v = await generate(client, review_id)
    after = v["indicators"]
    assert after is not None and after["total"] == 4
    checks = {c["id"]: c["passed"] for c in after["checks"]}
    assert list(checks) == [
        "selectable_text",
        "reading_order",
        "standard_headings",
        "contact_in_body",
        "font_sizes",
    ]
    assert checks["selectable_text"] and checks["standard_headings"]
    assert after["covered"] >= 1  # « Python » figure dans une ligne adossée à un fait
    page = await client.get(f"{API}/cv/versions/{v['id']}/pages/1")
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"
    assert (await client.get(f"{API}/cv/versions/{v['id']}/pages/2")).status_code == 404
