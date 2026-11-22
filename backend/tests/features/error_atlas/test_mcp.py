import httpx
from fastapi import FastAPI

from tests.features.error_atlas.support import HYPOTHESIS, seed_evidence
from tests.mcp.adapter_support import call
from tests.mcp.support import API, LOCAL, Mcp
from tests.mcp.test_direct_write import undo_last


async def test_mcp_records_private_evidence_and_reverses_exercise(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    await seed_evidence(app)
    token = await mcp.token(("error_atlas",), "write")
    available, failed = await call(mcp, token, "error_atlas_list_evidence")
    assert not failed, available
    reference = available["data"][0]["reference"]
    saved, failed = await call(
        mcp,
        token,
        "error_atlas_record_observation",
        {
            "reference": reference,
            "hypothesis": HYPOTHESIS,
            "confidence": "low",
        },
    )
    assert not failed, saved
    hypothesis_id = saved["data"]["id"]
    created, failed = await call(
        mcp, token, "error_atlas_choose_exercise", {"hypothesis_id": hypothesis_id}
    )
    assert not failed and created["data"]["id"], created
    undone = await undo_last(mcp)
    assert undone.status_code == 200, undone.text
    group = (await client.get(f"{API}/error-atlas")).json()[0]
    assert group["exercise"] is None
    assert group["observations"][0]["evidence"]["reference"] == reference
