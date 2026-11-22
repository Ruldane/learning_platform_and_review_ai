import httpx
from fastapi import FastAPI

from app.agents.tools.cv_compose import base_content
from app.features.cv.service.targeted_content import TargetedCvContent, compose_targeted_cv
from app.features.cv.service.versions import validated_profile
from app.features.portfolio.schemas import Candidate
from app.features.portfolio.service.links import approved_link
from app.features.portfolio.service.render import html
from tests.features.applications.kit_support import ready_application
from tests.features.applications.test_kit_zip import fetch
from tests.mcp.support import API

ORIGIN = "https://portfolio.example.test"


def test_static_source_links_use_the_same_window() -> None:
    source = Candidate(
        id="source",
        kind="github",
        label="Projet de recette",
        text="Commit vérifié",
        url="https://github.com/example/project/commit/123abc",
    )
    output = html([source])
    assert b'href="https://github.com/example/project/commit/123abc"' in output
    assert b'target="_blank"' not in output


async def _publish(client: httpx.AsyncClient) -> dict[str, str]:
    made = await client.post(f"{API}/portfolio/drafts", json={"selected": ["name"]})
    assert made.status_code == 201, made.text
    draft = made.json()
    approved = await client.post(
        f"{API}/portfolio/publish",
        json={
            "draft_id": draft["id"],
            "digest": draft["digest"],
            "destination": draft["destination"],
            "confirmed": True,
        },
    )
    assert approved.status_code == 200, approved.text
    return {"revision_id": draft["id"], "url": draft["destination"]}


async def test_link_is_explicit_for_new_cv_and_kit_and_cleared_on_replacement(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.settings.portfolio_public_origin = ORIGIN
    application = await ready_application(client, app)
    approved = await _publish(client)
    assert "08_portfolio.txt" not in (await fetch(client, application))[1].namelist()
    for target in ("cv", "kit"):
        accepted = await client.put(
            f"{API}/portfolio/links/{target}", json={**approved, "enabled": True}
        )
        assert accepted.status_code == 200, accepted.text
    _, archive = await fetch(client, application)
    assert archive.read("08_portfolio.txt").decode().strip() == approved["url"]
    async with app.state.session_factory() as db:
        user = app.state.local_user_id
        profile = await validated_profile(db, user)
        assert profile is not None
        link = await approved_link(db, user, "cv", ORIGIN)
        result = compose_targeted_cv(
            base_content(profile, ("experience", "skills")), profile, [], None, portfolio=link
        )
        assert isinstance(result.content, TargetedCvContent)
        assert result.content.header_links[-1].url == approved["url"]
    replaced = await _publish(client)
    assert replaced["revision_id"] != approved["revision_id"]
    assert "08_portfolio.txt" not in (await fetch(client, application))[1].namelist()
    async with app.state.session_factory() as db:
        assert await approved_link(db, app.state.local_user_id, "cv", ORIGIN) is None
