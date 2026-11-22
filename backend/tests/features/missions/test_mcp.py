import httpx
from fastapi import FastAPI

from tests.features.missions.support import seed_posting
from tests.mcp.adapter_support import call
from tests.mcp.support import API, LOCAL, Mcp
from tests.mcp.test_direct_write import undo_last


async def test_mcp_reverses_a_saved_measure_without_losing_the_mission(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    client.headers.update(LOCAL)
    claude = Mcp(client)
    posting = await seed_posting(app)
    token = await claude.token(("missions",), "write")
    started, failed = await call(
        claude, token, "missions_start_mission", {"posting_id": posting, "requirement_indices": [0]}
    )
    assert not failed, started
    mission_id = started["data"]["id"]
    path = f"{API}/missions/{mission_id}"
    progress, failed = await call(
        claude,
        token,
        "missions_update_criterion",
        {
            "mission_id": mission_id,
            "index": 0,
            "revision": 0,
            "observed": 1,
            "note": "Mesure fictive.",
        },
    )
    assert not failed, progress
    current = (await claude.http.get(path)).json()
    assert current["revision"] == 1 and current["criteria"][0]["note"] == "Mesure fictive."
    read, failed = await call(claude, token, "missions_get_mission", {"mission_id": mission_id})
    assert not failed, read
    assert read["data"]["revision"] == 1
    undone = await undo_last(claude)
    assert undone.status_code == 200, undone.text
    restored = (await claude.http.get(path)).json()
    assert restored["criteria"][0]["observed"] == 0
    assert restored["criteria"][0]["note"] is None
