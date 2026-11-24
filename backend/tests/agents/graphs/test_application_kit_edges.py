"""The kit's résumé branch and token budget (D142)."""

from app.agents.runtime.costs import TokenBudgetExceeded
from tests.agents.graphs.kit_support import MakeKit, writers
from tests.support.kit import FakeKitStore


async def test_cv_piece_points_at_the_latest_ready_version(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    run = await kit_runner()
    await run.wait_status("completed")
    cv = kit_store.piece("cv")
    assert (cv.status, cv.content, cv.meta) == (
        "ready",
        "Tailored résumé (version 3)",
        {"version_id": "version-3"},
    )


async def test_cv_piece_without_version_asks_for_the_review(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    kit_store.update(cv_version=None)
    run = await kit_runner()
    await run.wait_status("completed")
    cv = kit_store.piece("cv")
    assert cv.status == "to_check"
    assert cv.content == "Run the résumé review for this posting to create a tailored résumé."


async def test_token_cap_stops_the_session_instead_of_failing_pieces(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    models = writers()

    async def over_budget(agent: str, prompt: str) -> None:
        if "Write the cover letter." in prompt:
            raise TokenBudgetExceeded(1000)

    models.hooks.append(over_budget)
    run = await kit_runner(models)
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "token_cap_reached"
    assert all(r.status != "failed" for r in kit_store.rows.values())
