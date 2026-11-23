import httpx

from app.mcp.schema import never_reachable
from tests.mcp.adapter_support import call
from tests.mcp.support import LOCAL, Mcp


def test_calendar_consent_and_sync_routes_remain_private() -> None:
    assert not never_reachable("/calendar/upcoming")
    assert not never_reachable("/calendar/proposals")
    assert never_reachable("/calendar/connection", "POST")
    assert not never_reachable("/calendar/connection", "GET")
    assert never_reachable("/calendar/callback")
    assert not never_reachable("/calendar/proposals/{proposal_id}/confirm", "POST")


async def test_read_scope_can_reopen_local_calendar_and_portfolio(
    client: httpx.AsyncClient,
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("calendar", "portfolio"), "read")
    event, failed = await call(mcp, token, "calendar_read_upcoming", {})
    assert not failed, event
    assert event["data"] == {}
    site, failed = await call(mcp, token, "portfolio_read_private", {})
    assert not failed, site
    assert site["data"]["draft"] is None


async def test_preparations_wait_for_confirmation(client: httpx.AsyncClient) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    writer = await mcp.token(("calendar", "portfolio"), "write")
    selection = {"kind": "study", "program_id": "programme-fictif", "source_id": "semaine-fictive"}
    for name, arguments in (
        ("calendar_prepare_proposal", {"body": selection}),
        ("portfolio_prepare_draft", {"selected": ["preuve-fictive"]}),
    ):
        answer, failed = await call(mcp, writer, name, arguments)
        assert not failed, answer
        assert answer["data"]["status"] == "pending_confirmation"
        assert answer["data"]["confirmation_id"]
