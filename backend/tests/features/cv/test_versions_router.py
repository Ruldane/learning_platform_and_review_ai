"""API des versions du CV ciblé (D130) : liste par offre, détail, PDF téléchargé sous son nom
ASCII, images des pages ; une version en rendu dont la session s'arrête passe en échec."""

import httpx
from fastapi import FastAPI

from app.features.cv.service.runtime import CvRuntime
from tests.features.cv.reviews_support import (
    API,
    ResumeSpy,
    open_review,
    post_generate,
    set_session,
    version,
)
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.text_renderer import TextHtmlRenderer

VERSIONS = f"{API}/cv/versions"


async def test_pdf_download_headers(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    version_id = (await post_generate(client, review_id)).json()["version_id"]
    r = await client.get(f"{VERSIONS}/{version_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == (
        'attachment; filename="CV_Camille_Exemple_Societe_Fictive_AI_Product_Engineer.pdf"'
    )
    assert r.headers["cache-control"] == "no-store"
    assert r.content.startswith(b"%PDF")
    assert (await client.get(f"{VERSIONS}/inconnue/pdf")).status_code == 404


async def test_list_versions_by_posting(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, _ = await open_review(client, app)
    posting_id = (await client.get(f"{API}/cv/reviews/{review_id}")).json()["posting_id"]
    first = (await post_generate(client, review_id)).json()["version_id"]
    second = (await post_generate(client, review_id)).json()["version_id"]
    listed = (await client.get(VERSIONS, params={"posting_id": posting_id})).json()
    assert [item["id"] for item in listed] == [second, first]  # la plus récente d'abord
    assert (await client.get(VERSIONS, params={"posting_id": "autre"})).json() == []
    one = await version(client, first)
    assert (one["review_id"], one["posting_id"], one["number"]) == (review_id, posting_id, 1)
    missing = await client.get(f"{VERSIONS}/inconnue")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "version_not_found")


async def test_rendering_version_fails_with_its_session(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, session_id = await open_review(client, app)
    resume_spy.render = False
    version_id = (await post_generate(client, review_id)).json()["version_id"]
    assert (await version(client, version_id))["status"] == "rendering"
    rt: CvRuntime = app.state.career.cv
    await set_session(rt, session_id, "failed")  # panne pendant le rendu
    failed = await version(client, version_id)
    assert failed["status"] == "failed" and failed["failure_reason"]
    shown = (await client.get(f"{API}/cv/reviews/{review_id}")).json()
    assert shown["status"] == "failed"
