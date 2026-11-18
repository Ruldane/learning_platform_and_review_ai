import httpx
from sqlalchemy import update

from app.core.played import PLAY_CONTEXT, PlayContext
from app.db.models.daily import Project
from app.features.projects.service.runtime import BRIEF_GRAPH, REVIEW_GRAPH, SUBJECT
from tests.agents.runtime.runner_helpers import get_session
from tests.features.projects.support import API, Env, submit


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


async def test_drafts_relaunch_inherits_the_review_provider(
    client: httpx.AsyncClient, env: Env
) -> None:
    project_id = await env.add_project(status="validated", submissions=[env.last_submission()])
    flag = PLAY_CONTEXT.set(PlayContext(env.user_id, None, provider="glm"))
    try:
        review = await env.launcher.start(
            env.user_id, REVIEW_GRAPH, {"project_id": project_id}, subject_type=SUBJECT
        )
    finally:
        PLAY_CONTEXT.reset(flag)
    await env.launcher.end(env.user_id, review)
    async with env.app.state.session_factory() as db:
        await db.execute(update(Project).where(Project.id == project_id).values(session_id=review))
        await db.commit()

    out = await client.post(f"{API}/{project_id}/drafts")
    assert out.status_code == 202, out.json()
    row = await get_session(env.rt.session_factory, env.user_id, out.json()["session_id"])
    assert (row.played_by, row.model_provider) == (None, "glm")
