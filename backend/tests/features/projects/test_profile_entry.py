"""L'entrée d'un projet validé dans le profil maître (rule 5, P3, D166) : **seulement** par le clic
de January (`POST /profile-entry`), nouvelle version validée de source `january`, 409 lisibles,
jamais deux fois, jamais à la validation."""

import asyncio
from typing import Any

import httpx

from app.agents.tools.cv_schema import Project
from app.db.models.career import MasterProfile
from app.features.projects.service.store import AgentProjectStore
from tests.features.projects.support import API, Env, outcome
from tests.support.projects import REPO_URL

ENTRY: dict[str, Any] = {
    "name": "Suivi de lecture",
    "description": "Une API de suivi de lecture avec FastAPI.",
    "achievements": ["Trois routes documentées", "Des tests"],
}


async def validated(env: Env, **over: Any) -> str:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()], **over)
    await AgentProjectStore(env.rt).save_review(env.user_id, "s1", pid, outcome())
    return pid


async def enter(client: httpx.AsyncClient, pid: str, **body: Any) -> httpx.Response:
    return await client.post(f"{API}/{pid}/profile-entry", json=ENTRY | body)


def error(response: httpx.Response) -> str:
    code: str = response.json()["error"]["code"]
    return code


async def test_profile_unchanged_until_explicit_entry(env: Env, client: httpx.AsyncClient) -> None:
    await env.add_profile(3)
    pid = await validated(env)
    versions = await env.profile_versions()
    assert [v.version for v in versions] == [1, 2, 3] and not versions[-1].data["projects"]
    shown = (await client.get(f"{API}/{pid}")).json()
    assert shown["status"] == "validated" and shown["profile_version"] is None
    r = await enter(client, pid)
    assert r.status_code == 200
    assert r.json()["profile_version"] == 4 and r.json()["status"] == "validated"
    versions = await env.profile_versions()
    assert [(v.version, v.status, v.source) for v in versions][-1] == (4, "validated", "january")
    [project] = versions[-1].data["projects"]
    assert (project["name"], project["description"], project["link"]) == (
        ENTRY["name"],
        ENTRY["description"],
        REPO_URL,
    )
    assert [line["text"] for line in project["achievements"]] == ENTRY["achievements"]
    assert project["sources"] == ["january"] and project["id"]
    assert (
        versions[-1].data["experiences"] == versions[-2].data["experiences"]
    )  # le reste est gardé
    assert not versions[-2].data["projects"]  # les versions d'avant ne bougent pas
    assert (await client.get(f"{API}/{pid}")).json()["profile_version"] == 4


async def test_entry_already_added_409(env: Env, client: httpx.AsyncClient) -> None:
    await env.add_profile(1)
    pid = await validated(env)
    assert (await enter(client, pid)).status_code == 200
    again = await enter(client, pid, name="Autre nom")
    assert again.status_code == 409 and error(again) == "entry_already_added"
    assert len(await env.profile_versions()) == 2


async def test_a_double_click_adds_the_project_once(env: Env, client: httpx.AsyncClient) -> None:
    await env.add_profile(1)
    pid = await validated(env)
    first, second = await asyncio.gather(enter(client, pid), enter(client, pid))
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    versions = await env.profile_versions()
    assert [len(v.data["projects"]) for v in versions] == [0, 1]


async def test_only_a_validated_project_enters_the_profile(
    env: Env, client: httpx.AsyncClient
) -> None:
    await env.add_profile(1)
    for module, status in enumerate(("todo", "to_redo")):
        pid = await env.add_project(module, status=status)
        r = await enter(client, pid)
        assert r.status_code == 409 and error(r) == "project_not_validated"
    assert len(await env.profile_versions()) == 1


async def test_profile_required_without_a_validated_profile(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await validated(env)
    r = await enter(client, pid)
    assert r.status_code == 409 and error(r) == "profile_required"


async def test_a_pending_profile_draft_blocks_the_entry(
    env: Env, client: httpx.AsyncClient
) -> None:
    await env.add_profile(2)
    async with env.app.state.session_factory() as db:
        last = (await env.profile_versions())[-1]
        db.add(
            MasterProfile(
                user_id=env.user_id, version=3, status="draft", data=last.data, source="archivist"
            )
        )
        await db.commit()
    pid = await validated(env)
    r = await enter(client, pid)
    assert r.status_code == 409 and error(r) == "profile_draft_pending"
    assert len(await env.profile_versions()) == 3 and (await env.row(pid)).profile_version is None


async def test_profile_projects_full_at_twenty(env: Env, client: httpx.AsyncClient) -> None:
    await env.add_profile(1, projects=[Project(name=f"Projet {n}") for n in range(20)])
    pid = await validated(env)
    r = await enter(client, pid)
    assert r.status_code == 409 and error(r) == "profile_projects_full"


async def test_a_long_repo_link_is_left_out_of_the_entry(
    env: Env, client: httpx.AsyncClient
) -> None:
    await env.add_profile(1)
    submission = env.last_submission() | {"repo_url": "https://example.org/" + "a" * 400}
    pid = await env.add_project(status="reviewing", submissions=[submission])
    await AgentProjectStore(env.rt).save_review(env.user_id, "s1", pid, outcome())
    assert (await enter(client, pid)).status_code == 200
    [project] = (await env.profile_versions())[-1].data["projects"]
    assert project["link"] is None


async def test_entry_body_is_validated_without_echo(env: Env, client: httpx.AsyncClient) -> None:
    await env.add_profile(1)
    pid = await validated(env)
    for body, field in [
        ({"name": ""}, "name"),
        ({"description": "secrète " * 100}, "description"),
        ({"achievements": ["un"] * 5}, "achievements"),
        ({"achievements": ["x" * 201]}, "achievements.0"),
    ]:
        r = await enter(client, pid, **body)
        assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": [field]}
        assert "secrète" not in r.text
    assert len(await env.profile_versions()) == 1


async def test_entry_of_another_users_project_is_404(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project(user="autre-utilisatrice", status="validated")
    r = await enter(client, pid)
    assert r.status_code == 404 and error(r) == "project_not_found"


async def test_the_validation_by_the_port_never_writes_the_profile(env: Env) -> None:
    await env.add_profile(2)
    await validated(env)
    assert [v.version for v in await env.profile_versions()] == [1, 2]
