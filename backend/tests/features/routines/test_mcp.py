from uuid import uuid4

import httpx

from tests.mcp.adapter_support import call
from tests.mcp.support import LOCAL, Mcp


async def test_mcp_configures_and_runs_an_owned_routine(client: httpx.AsyncClient) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    write_token = await mcp.token(("routines",), "write")
    created, failed = await call(
        mcp, write_token, "routines_rule_create", {"action": "due_reviews", "local_time": "08:30"}
    )
    assert not failed, created
    routine_id = created["data"]["id"]
    arguments = {"routine_id": routine_id, "receipt": str(uuid4())}
    run, failed = await call(mcp, write_token, "routines_execution_start", arguments)
    assert not failed, run
    replay, failed = await call(mcp, write_token, "routines_execution_start", arguments)
    assert not failed, replay
    assert run["data"] == replay["data"]

    read_token = await mcp.token(("routines",), "read")
    history, failed = await call(
        mcp, read_token, "routines_executions_list", {"routine_id": routine_id}
    )
    assert not failed, history
    assert history["data"] == [run["data"]]
