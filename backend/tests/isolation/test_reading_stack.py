from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reading_stack.repository import ReadingRepository
from app.features.reading_stack.types import CollectedItem
from tests.isolation.conftest import Browser

API = "/api/v1/reading-stack"


async def _seed(db: AsyncSession, owner: httpx.AsyncClient) -> tuple[str, str]:
    me = await owner.get("/api/v1/auth/me")
    repo = ReadingRepository(db, me.json()["id"])
    now = datetime.now(UTC)
    article = await repo.record(
        CollectedItem(
            "article", "https://example.org/read", "Un guide", "Résumé.", "Texte.", "Test"
        ),
        now,
    )
    offer = await repo.record(
        CollectedItem(
            "offer",
            "https://example.org/offer",
            "Développer en Python",
            "Offre",
            "",
            "Radar",
            "Entreprise Fictive",
        ),
        now,
    )
    await db.commit()
    assert article is not None and offer is not None
    return article, offer


async def _reject_foreign(browser: httpx.AsyncClient, item: str) -> None:
    for method, suffix, body in (
        ("GET", "", None),
        ("PATCH", "", {"read": True}),
        ("POST", "/memory", None),
        ("POST", "/cards", None),
        ("POST", "/plan", {"program_id": "programme"}),
        ("POST", "/application", {"company": "Entreprise Fictive"}),
    ):
        result = await browser.request(method, API + "/" + item + suffix, json=body)
        assert result.status_code == 404, result.text


async def test_reading_sources_items_and_actions_are_private(
    google_client_factory: Browser, db_session: AsyncSession
) -> None:
    owner = await google_client_factory("january@example.com")
    other = await google_client_factory("autre@example.com")
    source = await owner.post(
        f"{API}/sources",
        json={"kind": "site", "label": "Python", "value": "https://example.org/lib"},
    )
    assert source.status_code == 201 and source.json()["value"] == "example.org"
    src = f"{API}/sources/{source.json()['id']}"
    assert (await other.get(f"{API}/sources")).json() == []
    assert (await other.patch(src, json={"active": False})).status_code == 404
    assert (await other.delete(src)).status_code == 404
    item, offer = await _seed(db_session, owner)

    assert (await other.get(API)).json()["unread_count"] == 0
    await _reject_foreign(other, item)
    assert (await owner.get(f"{API}/{item}")).json()["text"] == "Texte."
    assert (await owner.patch(f"{API}/{item}", json={"read": True})).json()["read_at"]
    assert (await owner.get(API, params={"unread": True})).json()["unread_count"] == 1
    assert (await owner.post(f"{API}/{item}/cards")).json()["count"] == 1
    assert (await owner.post(f"{API}/{item}/cards")).json()["count"] == 0
    assert (await owner.post(f"{API}/{item}/memory")).json()["memory_item_id"]

    body = {"company": "Entreprise Fictive"}
    assert (await owner.post(f"{API}/{offer}/application", json=body)).status_code == 201
    assert (await owner.post(f"{API}/{offer}/application", json=body)).status_code == 409
