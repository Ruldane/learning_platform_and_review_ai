import io
import zipfile
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.portfolio_urls import normalize_origin
from tests.mcp.support import API

ORIGIN = "https://portfolio.exemple.test"


async def _private_preview(client: httpx.AsyncClient) -> tuple[dict[str, Any], bytes]:
    profile = await client.put(
        f"{API}/profile",
        json={
            "data": {
                "identity": {"name": "<Mina & Co>", "email": "prive@example.test"},
                "summary": {"text": "Notice privée retenue hors du site."},
            }
        },
    )
    assert profile.status_code == 200, profile.text
    base = f"{API}/portfolio"
    opened = await client.get(base)
    assert opened.status_code == 200, opened.text
    assert opened.json()["publication"] is None
    first = await client.post(f"{base}/drafts", json={"selected": ["name"]})
    assert first.status_code == 201, first.text
    draft = first.json()
    prefix = f"{base}/drafts/{draft['id']}"
    shown = await client.get(f"{prefix}/preview")
    assert shown.status_code == 200 and "no-store" in shown.headers["cache-control"]
    assert "&lt;Mina &amp; Co&gt;" in shown.text
    assert "prive@example.test" not in shown.text and "Notice privée" not in shown.text
    zipped = await client.get(f"{prefix}/zip")
    with zipfile.ZipFile(io.BytesIO(zipped.content)) as archive:
        assert archive.namelist() == ["index.html"]
        assert archive.read("index.html") == shown.content
    return draft, shown.content


async def test_publication_requires_the_exact_private_preview_and_can_be_replaced_and_withdrawn(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.settings.portfolio_public_origin = ORIGIN
    base = f"{API}/portfolio"
    draft, content = await _private_preview(client)
    public_path = draft["destination"].removeprefix(ORIGIN)
    public_host = {"Host": "portfolio.exemple.test"}
    assert (await client.get(f"{API}/profile", headers=public_host)).status_code == 404
    assert (await client.get(public_path, headers=public_host)).status_code == 404
    body = {
        "draft_id": draft["id"],
        "digest": draft["digest"],
        "destination": draft["destination"],
        "confirmed": True,
    }
    assert (
        await client.post(f"{base}/publish", json=body | {"digest": "0" * 64})
    ).status_code == 409
    assert (
        await client.post(f"{base}/publish", json=body | {"confirmed": False})
    ).status_code == 422
    assert (await client.post(f"{base}/publish", json=body)).status_code == 200
    assert (await client.get(public_path, headers=public_host)).content == content

    second = await client.post(f"{base}/drafts", json={"selected": ["summary"]})
    replacement = second.json()
    assert replacement["destination"] == draft["destination"]
    assert (await client.get(public_path, headers=public_host)).content == content
    assert (await client.post(f"{base}/publish", json=body)).status_code == 409
    new_body = body | {"draft_id": replacement["id"], "digest": replacement["digest"]}
    assert (await client.post(f"{base}/publish", json=new_body)).status_code == 200
    assert "Notice privée" in (await client.get(public_path, headers=public_host)).text
    withdrawal = {key: value for key, value in new_body.items() if key != "digest"}
    withdrawn = await client.post(f"{base}/withdraw", json=withdrawal)
    assert withdrawn.status_code == 200, withdrawn.text
    assert (await client.get(public_path, headers=public_host)).status_code == 404
    assert (await client.post(f"{base}/publish", json=new_body)).status_code == 409
    assert (await client.get(public_path, headers=public_host)).status_code == 404
    assert (await client.get(base)).json()["draft"] is None
    assert (await client.get(f"{base}/drafts/{replacement['id']}/preview")).status_code == 200


@pytest.mark.parametrize(
    ("configured", "canonical"),
    [
        (ORIGIN + ":443", ORIGIN),
        ("http://localhost:80", "http://localhost"),
        ("https://portfolio.exemple.test:8443", "https://portfolio.exemple.test:8443"),
    ],
)
def test_public_origin_omits_only_the_default_port(configured: str, canonical: str) -> None:
    assert normalize_origin(configured) == canonical


async def draft_offer(client: httpx.AsyncClient, selected: str) -> dict[str, Any]:
    response = await client.post(f"{API}/portfolio/drafts", json={"selected": [selected]})
    assert response.status_code == 201, response.text
    result = response.json()
    return {
        "draft_id": result["id"],
        "digest": result["digest"],
        "destination": result["destination"],
        "confirmed": True,
    }


async def test_public_host_accepts_default_port_and_withdraw_keeps_another_draft(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.settings.portfolio_public_origin = ORIGIN
    base = f"{API}/portfolio"
    profile = await client.put(
        f"{API}/profile",
        json={"data": {"identity": {"name": "Mina"}, "summary": {"text": "Autre version"}}},
    )
    assert profile.status_code == 200
    ready = await draft_offer(client, "name")
    assert (await client.post(f"{base}/publish", json=ready)).status_code == 200
    public_path = ready["destination"].removeprefix(ORIGIN)
    for authority in ("portfolio.exemple.test", "PORTFOLIO.EXEMPLE.TEST:443"):
        headers = {"Host": authority}
        assert (await client.get(f"{API}/profile", headers=headers)).status_code == 404
        assert (await client.get(public_path, headers=headers)).status_code == 200
    assert (
        await client.get(public_path, headers={"Host": "portfolio.exemple.test:8443"})
    ).status_code == 404

    next_draft = await draft_offer(client, "summary")
    withdrawn = {key: value for key, value in ready.items() if key != "digest"}
    assert (await client.post(f"{base}/withdraw", json=withdrawn)).status_code == 200
    assert (await client.get(base)).json()["draft"]["id"] == next_draft["draft_id"]
    assert (await client.post(f"{base}/publish", json=next_draft)).status_code == 200
