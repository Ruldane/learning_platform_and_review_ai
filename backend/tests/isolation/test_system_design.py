import httpx
from fastapi import FastAPI

from app.core.deps import CurrentUser, get_interface_user
from tests.mcp.support import API
from tests.sessions_support import act_as


async def test_system_design_board_and_review_are_private(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    response = await client.post(
        f"{API}/interviews", json={"mode": "case", "duration_min": 30, "system_design": True}
    )
    assert response.status_code == 202
    interview_id = response.json()["interview_id"]
    path = f"{API}/interviews/{interview_id}/design"
    board_id = (await client.get(path)).json()["board"]["id"]

    act_as(app, "second-account")
    app.dependency_overrides[get_interface_user] = lambda: CurrentUser(
        id="second-account", email=None
    )
    assert (await client.get(f"{API}/system-design")).json() is None
    assert (await client.get(path)).status_code == 404
    edited = await client.post(
        f"{API}/boards/{board_id}/edits", json={"scene": {"elements": []}, "note": "Dessin"}
    )
    assert edited.status_code == 404
