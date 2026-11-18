import httpx

from app.core.played import PLAY_CONTEXT, PlayContext
from app.features.projects.service.runtime import BRIEF_GRAPH, SUBJECT
from tests.agents.runtime.runner_helpers import get_session
from tests.features.projects.support import Env, submit


async def test_january_submission_inherits_the_project_brief_client(
    client: httpx.AsyncClient, env: Env
) -> None:
    project_id = await env.add_project()
    flag = PLAY_CONTEXT.set(PlayContext(env.user_id, "codex"))
    try:
        sid = await env.launcher.start(
            env.user_id,
            BRIEF_GRAPH,
            {"project_id": project_id},
            subject_type=SUBJECT,
            subject_id=project_id,
        )
    finally:
        PLAY_CONTEXT.reset(flag)
    await env.launcher.end(env.user_id, sid)

    out = await submit(client, project_id)
    assert out.status_code == 202, out.json()
    row = await get_session(env.rt.session_factory, env.user_id, out.json()["session_id"])
    assert row.played_by == "codex" and row.graph == "project_review"
