"""Les fiches ajoutées en direct suivent la même lecture et le même historique que les autres."""

import httpx
import pytest
from fastapi import FastAPI

from tests.features.lessons.test_router import seed
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.sessions_support import act_as
from tests.support.direct import Seed, assert_no_agent, lesson_text

pytestmark = pytest.mark.usefixtures("settled_indexing")
MARKDOWN = lesson_text("Un cours avec une lecture conseillée.")
ARTICLE = {
    "url": "https://exemple.org/article#resultats",
    "title": "Évaluer la récupération",
    "type": "article",
    "author": "Sam Exemple",
    "lang": "fr",
    "reason": "Lire les résultats et repérer la métrique de classement.",
}


async def test_lesson_write_includes_trackable_resource(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, claude: Mcp
) -> None:
    token = await claude.token(("lessons",), "write")
    result, error = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": MARKDOWN, "resources": [ARTICLE]},
    )

    assert not error, result
    [resource] = result["data"]["resources"]
    assert resource["status"] == "to_read"
    assert resource["title"] == "<donnee_non_fiable>Évaluer la récupération</donnee_non_fiable>"
    assert resource["url"] == ARTICLE["url"]
    library = (
        await client.get(f"{API}/resources", params={"program_id": drafted.program_id})
    ).json()
    assert [row["id"] for row in library] == [resource["id"]]
    await assert_no_agent(app)


async def test_attach_to_ready_lesson_preserves_read_status_and_is_reversible(
    client: httpx.AsyncClient, app: FastAPI, claude: Mcp
) -> None:
    seeded = await seed(app)
    path = f"{API}/lessons/{seeded.lesson_id}"
    lesson = (await client.get(path)).json()
    token = await claude.token(("lessons",), "write")
    same = {**ARTICLE, "url": "https://SITE2.exemple.org/page#conclusion"}

    result, error = await call(
        claude,
        token,
        "lessons_update_lesson",
        {"lesson_id": seeded.lesson_id, "resources": [same, ARTICLE, ARTICLE]},
    )

    assert not error, result
    assert result["data"]["markdown"] == lesson["markdown"]
    assert result["data"]["word_count"] == lesson["word_count"]
    assert result["data"]["pdf_available"] is True
    _, _, previous, added = result["data"]["resources"]
    assert (previous["id"], previous["status"]) == (seeded.resources[2], "read")
    assert (added["url"], added["status"]) == (ARTICLE["url"], "to_read")
    [change] = (await claude.http.get(f"{API}/mcp/changes")).json()
    undone = await claude.http.post(f"{API}/mcp/changes/{change['call_id']}/undo")
    assert undone.status_code == 200, undone.text
    assert (await client.get(path)).json()["resources"] == lesson["resources"]


async def test_cannot_attach_to_another_users_lesson(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    seeded = await seed(app)
    act_as(app, "autre-utilisatrice")

    response = await client.patch(
        f"{API}/lessons/{seeded.lesson_id}", json={"resources": [ARTICLE]}
    )

    assert response.status_code == 404
    assert (await client.get(f"{API}/resources")).json() == []


@pytest.mark.parametrize("bad_url", ["javascript:alert(1)", "http://login:secret@example.org/"])
async def test_invalid_resource_prevents_lesson_write(
    client: httpx.AsyncClient, drafted: Seed, bad_url: str
) -> None:
    response = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson",
        json={"markdown": MARKDOWN, "resources": [{**ARTICLE, "url": bad_url}]},
    )

    assert response.status_code == 422
    assert bad_url not in response.text
    assert (await client.get(f"{API}/programs/{drafted.program_id}/lessons")).json() == []
