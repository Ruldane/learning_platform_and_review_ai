"""La délégation prépare l’épreuve, la confirmation précède le coût du modèle."""

from fastapi import FastAPI

from tests.features.blind_assessment.support import seed_versions
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp


async def test_mcp_create_is_private_and_evaluate_waits_for_confirmation(
    app: FastAPI, claude: Mcp
) -> None:
    first, second = await seed_versions(app, app.state.local_user_id)
    token = await claude.token(("blind_assessment",), "write")
    chosen = {"first_version_id": first, "second_version_id": second, "rubric": "evidence"}
    saved, failed = await call(claude, token, "blind_assessment_create", chosen)
    assert not failed, saved
    trial = saved["data"]
    assert trial["result"] is None
    assert first not in str(trial) and second not in str(trial)
    pending, failed = await call(
        claude, token, "blind_assessment_evaluate", {"assessment_id": trial["id"]}
    )
    assert not failed, pending
    assert pending["data"]["status"] == "pending_confirmation"
    result = await claude.http.get(f"{API}/blind-assessments/{trial['id']}")
    assert result.json()["stage"] == "draft"
    assert result.json()["result"] is None
