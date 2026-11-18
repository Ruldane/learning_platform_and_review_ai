from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.mcp.test_direct_write import undo_last


async def test_mcp_skill_can_be_added_and_undone(claude: Mcp) -> None:
    token = await claude.token(("skills",), "write")
    result, failed = await call(
        claude, token, "skills_write_skill", {"name": "Analyse SQL", "domain": "Données"}
    )
    assert not failed, result
    path = f"{API}/skills/{result['data']['id']}"
    skill = (await claude.http.get(path)).json()
    assert skill["level"] is None and skill["evidence"] == []
    undone = await undo_last(claude)
    assert undone.status_code == 200, undone.text
    assert (await claude.http.get(path)).status_code == 404
