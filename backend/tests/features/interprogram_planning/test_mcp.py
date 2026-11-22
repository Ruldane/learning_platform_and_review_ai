import httpx
from fastapi import FastAPI

from tests.features.interprogram_planning.support import MONDAY, dates, seed_week
from tests.mcp.adapter_support import call
from tests.mcp.support import API, LOCAL, Mcp
from tests.mcp.test_direct_write import undo_last


async def test_mcp_can_undo_the_applied_week_and_all_its_task_dates(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("interprogram_planning",), "write")
    programs, tasks = await seed_week(app)
    path = f"{API}/interprogram-planning"
    preview = await client.post(
        path, json={"week_start": MONDAY.isoformat(), "program_ids": programs}
    )
    assert preview.status_code == 201, preview.text
    accepted, failed = await call(
        mcp,
        token,
        "interprogram_planning_accept_week",
        {
            "proposal_id": preview.json()["id"],
            "confirmed": True,
        },
    )
    assert not failed, accepted
    assert accepted["data"]["status"] == "accepted"
    assert await dates(app, tasks) != [MONDAY] * 3
    undone = await undo_last(mcp)
    assert undone.status_code == 200, undone.text
    assert await dates(app, tasks) == [MONDAY] * 3
    assert (await client.get(path)).json()[0]["status"] == "pending"
