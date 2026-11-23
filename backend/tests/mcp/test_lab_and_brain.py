import httpx

from tests.mcp.adapter_support import call
from tests.mcp.support import LOCAL, Mcp


async def test_lab_prefs_mcp_write_and_brain_folder_wait_for_confirmation(
    client: httpx.AsyncClient,
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("lab", "brain"), "write")
    update, failed = await call(mcp, token, "lab_change_preferences", {"pinned": ["oncall"]})
    assert not failed, update
    assert update["data"]["pinned"] == ["oncall"]
    read, failed = await call(mcp, token, "lab_read_preferences", {})
    assert not failed, read
    assert read["data"]["pinned"] == ["oncall"]

    task, failed = await call(
        mcp, token, "brain_add_folder", {"name": "Notes de test", "path": "C:/notes-fictives"}
    )
    assert not failed, task
    assert task["data"]["status"] == "pending_confirmation"
    assert (await client.get("/api/v1/brain/folders")).json() == []
