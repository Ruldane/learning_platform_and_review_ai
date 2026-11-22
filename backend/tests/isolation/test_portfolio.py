import httpx
from fastapi import FastAPI

from app.core.deps import CurrentUser, get_interface_user
from tests.mcp.support import API


async def test_other_account_cannot_read_or_publish_a_private_portfolio(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.settings.portfolio_public_origin = "https://portfolio.example.test"
    await client.put(f"{API}/profile", json={"data": {"identity": {"name": "Titulaire"}}})
    path = f"{API}/portfolio"
    draft = (await client.post(path + "/drafts", json={"selected": ["name"]})).json()
    app.dependency_overrides[get_interface_user] = lambda: CurrentUser(id="other-owner", email=None)
    assert (await client.get(path)).json() == {"candidates": [], "draft": None, "publication": None}
    for kind in ("preview", "zip"):
        assert (await client.get(f"{path}/drafts/{draft['id']}/{kind}")).status_code == 404
    answer = await client.post(
        path + "/publish",
        json={
            "draft_id": draft["id"],
            "destination": draft["destination"],
            "digest": draft["digest"],
            "confirmed": True,
        },
    )
    assert answer.status_code == 409
