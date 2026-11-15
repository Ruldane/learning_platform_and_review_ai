"""Le CV de l'entretien blanc (D146) : la version envoyée avec la fiche, sinon la plus récente prête
de l'offre, arrive dans `InterviewContext.cv_content` ; une version en rendu n'y est pas."""

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.interview_schema import InterviewContext
from tests.features.applications.conftest import add_posting, add_version
from tests.features.applications.interview_support import (
    BODY,
    ROOT,
    add_profile,
    interview_store,
    ready_application,
    send_version,
    set_version_content,
    spy,
)

pytestmark = pytest.mark.usefixtures("client")


async def _context(app: FastAPI, started: dict[str, str]) -> InterviewContext:
    return await interview_store(app).context(str(app.state.local_user_id), started["interview_id"])


async def test_latest_ready_version_of_the_posting(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    posting_id = await add_posting(app)
    first = await add_version(app, posting_id, number=1)
    second = await add_version(app, posting_id, number=2)
    rendering = await add_version(app, posting_id, number=3, status="rendering")
    for version_id, headline in ((first, "Version un"), (second, "Version deux")):
        await set_version_content(app, version_id, headline)
    await set_version_content(app, rendering, "Version en rendu")
    application_id = await ready_application(client, app, posting_id=posting_id)
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    ctx = await _context(app, r.json())
    assert ctx.cv_content is not None and ctx.cv_content.headline == "Version deux"


async def test_version_sent_with_the_application_wins(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    spy(app)
    posting_id = await add_posting(app)
    first = await add_version(app, posting_id, number=1)
    second = await add_version(app, posting_id, number=2)
    await set_version_content(app, first, "Version envoyée")
    await set_version_content(app, second, "Version plus récente")
    application_id = await ready_application(client, app, posting_id=posting_id)
    await send_version(app, application_id, first)
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    ctx = await _context(app, r.json())
    assert ctx.cv_content is not None and ctx.cv_content.headline == "Version envoyée"


async def test_free_interview_on_a_posting_reads_its_ready_version(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    spy(app)
    await add_profile(app)
    posting_id = await add_posting(app)
    version_id = await add_version(app, posting_id, number=1)
    await set_version_content(app, version_id, "Version de l'offre")
    r = await client.post(f"{ROOT}/interviews", json=BODY | {"posting_id": posting_id})
    ctx = await _context(app, r.json())
    assert ctx.cv_content is not None and ctx.cv_content.headline == "Version de l'offre"
