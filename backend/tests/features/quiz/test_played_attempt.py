import httpx

from app.core.played import PLAY_CONTEXT, PlayContext
from tests.agents.runtime.runner_helpers import get_session
from tests.features.quiz.conftest import Seeded
from tests.features.quiz.support import post_attempt, ready_quiz


async def test_january_attempt_inherits_the_quiz_client(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(seeded.user_id, "claude-code"))
    try:
        quiz_id = await ready_quiz(seeded)
    finally:
        PLAY_CONTEXT.reset(flag)

    out = await post_attempt(client, quiz_id)
    assert out.status_code == 202, out.json()
    row = await get_session(seeded.rt.session_factory, seeded.user_id, out.json()["session_id"])
    assert row.played_by == "claude-code" and row.input["mode"] == "grade"
