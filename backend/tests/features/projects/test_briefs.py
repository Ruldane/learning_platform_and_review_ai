"""Les énoncés des mini projets (P1, D166) : un projet par module non sauté dont la semaine a
commencé, une session `project_brief` lancée par celui qui insère, trois essais puis « Réessayer »,
le statut qui suit la session (au démarrage comme à la lecture)."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.db.models.program import Module
from app.features.projects.service.briefs import ensure_project_briefs
from tests.features.projects.support import API, WEEK_1, WEEK_2, Env
from tests.features.study.conftest import seed


def _briefs(env: Env) -> list[tuple[str, dict[str, str]]]:
    return [call for call in env.launcher.started if call[0] == "project_brief"]


async def test_week_start_creates_project_and_brief_session(env: Env) -> None:
    env.at(WEEK_1)
    assert await ensure_project_briefs(env.rt, WEEK_1) == 1
    assert await ensure_project_briefs(env.rt, WEEK_1) == 0  # deuxième passage : rien de plus
    [row] = await env.projects()
    assert (row.module_id, row.status, row.title) == (
        env.modules[0],
        "brief_pending",
        "Module Bases",
    )
    assert (row.program_id, row.brief_attempts, row.brief) == (env.seeded.program_id, 1, None)
    assert _briefs(env) == [("project_brief", {"project_id": row.id})]
    assert row.session_id is not None
    env.at(WEEK_2)  # la semaine suivante : le second module a son projet
    assert await ensure_project_briefs(env.rt, WEEK_2) == 1
    assert len(await env.projects()) == 2 and len(_briefs(env)) == 2


async def test_concurrent_passes_create_one_project_and_one_session(env: Env) -> None:
    results = await asyncio.gather(*(ensure_project_briefs(env.rt, WEEK_1) for _ in range(3)))
    assert sorted(results) == [0, 0, 1]
    assert len(await env.projects()) == 1 and len(_briefs(env)) == 1


async def test_skipped_module_gets_no_project(env: Env) -> None:
    async with env.app.state.session_factory() as db:
        await db.execute(update(Module).where(Module.id == env.modules[1]).values(skipped=True))
        await db.commit()
    assert await ensure_project_briefs(env.rt, WEEK_2) == 1
    [row] = await env.projects()
    assert row.module_id == env.modules[0]


async def test_draft_program_gets_no_project(client: httpx.AsyncClient, app: FastAPI) -> None:
    await seed(app, validated=False)
    assert await ensure_project_briefs(app.state.daily.projects, WEEK_2) == 0


async def test_week_start_is_the_local_monday(env: Env) -> None:
    sunday_night = datetime(2026, 11, 22, 22, 30, tzinfo=UTC)  # 23 h 30 à Paris, encore dimanche
    assert await ensure_project_briefs(env.rt, sunday_night) == 1  # semaine 1 seulement
    monday_local = datetime(2026, 11, 22, 23, 30, tzinfo=UTC)  # 00 h 30 à Paris : lundi
    assert await ensure_project_briefs(env.rt, monday_local) == 1
    assert len(await env.projects()) == 2


async def test_refused_launch_leaves_the_project_pending_and_retries_later(env: Env) -> None:
    env.at(WEEK_1)
    env.launcher.refuse = True
    assert await ensure_project_briefs(env.rt, WEEK_1) == 1
    [row] = await env.projects()
    assert row.status == "brief_pending" and row.session_id is None and not env.launcher.started
    env.launcher.refuse = False
    later = WEEK_1 + timedelta(minutes=6)  # au-delà du temps de lancer la session
    env.at(later)
    await ensure_project_briefs(env.rt, later)
    row = await env.row(row.id)
    assert row.session_id is not None and row.brief_attempts == 2
    assert len(_briefs(env)) == 1


async def _end(env: Env, project_id: str, status: str) -> None:
    row = await env.row(project_id)
    assert row.session_id is not None
    await env.launcher.end(env.user_id, row.session_id, status)


async def test_brief_failed_after_three_attempts_then_retry_route(
    env: Env, client: httpx.AsyncClient
) -> None:
    await ensure_project_briefs(env.rt, WEEK_1)
    [first] = await env.projects()
    for attempt in (2, 3):
        await _end(env, first.id, "failed")
        await ensure_project_briefs(env.rt, WEEK_1)
        row = await env.row(first.id)
        assert row.status == "brief_pending" and row.brief_attempts == attempt
        assert row.session_id is not None
    await _end(env, first.id, "failed")
    await ensure_project_briefs(env.rt, WEEK_1)
    row = await env.row(first.id)
    assert (row.status, row.brief_attempts, row.session_id) == ("brief_failed", 3, None)
    assert len(_briefs(env)) == 3  # jamais un quatrième essai automatique
    await ensure_project_briefs(env.rt, WEEK_1)
    assert len(_briefs(env)) == 3
    shown = (await client.get(f"{API}/{first.id}")).json()
    assert shown["status"] == "brief_failed" and shown["session_id"] is None
    retried = await client.post(f"{API}/{first.id}/brief")
    assert retried.status_code == 202
    row = await env.row(first.id)
    assert retried.json() == {"session_id": row.session_id}
    assert (row.status, row.brief_attempts) == ("brief_pending", 1)
    again = await client.post(f"{API}/{first.id}/brief")  # plus en échec : 409
    assert again.status_code == 409 and again.json()["error"]["code"] == "brief_not_failed"


async def test_retry_with_refused_launch_stays_failed_with_503(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project(status="brief_failed", brief=False, brief_attempts=3)
    env.launcher.refuse = True
    r = await client.post(f"{API}/{pid}/brief")
    assert r.status_code == 503 and r.json()["error"]["code"] == "brief_unavailable"
    assert (await env.row(pid)).status == "brief_failed"


async def test_cancelled_brief_session_is_not_retried(env: Env) -> None:
    await ensure_project_briefs(env.rt, WEEK_1)
    [row] = await env.projects()
    await _end(env, row.id, "cancelled")
    await ensure_project_briefs(env.rt, WEEK_1)
    row = await env.row(row.id)
    assert row.status == "brief_failed" and len(_briefs(env)) == 1


async def _review_session(env: Env, project_id: str) -> str:
    sid = await env.launcher.start(
        env.user_id,
        "project_review",
        {"project_id": project_id},
        subject_type="project",
        subject_id=project_id,
    )
    await env.patch(project_id, session_id=sid)
    return sid


async def test_startup_pass_reconciles_a_review_whose_session_died(env: Env) -> None:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await env.launcher.end(env.user_id, await _review_session(env, pid), "failed")
    await ensure_project_briefs(env.rt, WEEK_2)
    row = await env.row(pid)
    assert (row.status, row.session_id) == ("todo", None)


async def test_a_running_session_is_left_alone_at_startup(env: Env) -> None:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await _review_session(env, pid)
    await ensure_project_briefs(env.rt, WEEK_2)
    assert (await env.row(pid)).status == "reviewing"


async def test_reading_a_pending_brief_with_a_dead_last_session_says_failed(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project(brief=False, status="brief_pending", brief_attempts=3)
    sid = await env.launcher.start(
        env.user_id, "project_brief", {"project_id": pid}, subject_type="project", subject_id=pid
    )
    await env.patch(pid, session_id=sid)
    assert (await client.get(f"{API}/{pid}")).json()["status"] == "brief_pending"  # en cours
    await env.launcher.end(env.user_id, sid, "failed")
    shown = (await client.get(f"{API}/{pid}")).json()
    assert shown["status"] == "brief_failed" and shown["session_id"] is None
    early = await env.add_project(1, brief=False, status="brief_pending", brief_attempts=1)
    sid = await env.launcher.start(
        env.user_id,
        "project_brief",
        {"project_id": early},
        subject_type="project",
        subject_id=early,
    )
    await env.patch(early, session_id=sid)
    await env.launcher.end(env.user_id, sid, "failed")
    # sous la limite d'essais, la lecture ne tranche pas : la tâche relancera un essai
    assert (await client.get(f"{API}/{early}")).json()["status"] == "brief_pending"
