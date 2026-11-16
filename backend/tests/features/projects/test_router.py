"""Lectures des projets (14.2, D166) : le Portfolio (programme, semaine, rang), un projet (énoncé,
rendus du dernier au premier, évaluation avec ses critères, brouillons dans l'ordre), les captures
(type d'origine, jamais en cache), l'isolation par utilisatrice, le journal."""

import httpx

from app.features.projects.service.store import AgentProjectStore
from tests.features.projects.support import API, JPEG, PNG, WEBP, Env, outcome, shots, submit
from tests.support.projects import CRITERIA, DESCRIPTION, REPO_URL, TITLE


async def test_portfolio_lists_program_week_and_rank(env: Env, client: httpx.AsyncClient) -> None:
    second = await env.add_project(1, status="todo")
    first = await env.add_project(0, status="brief_pending", brief=False, title="Module Bases")
    listed = (await client.get(API)).json()
    assert [item["id"] for item in listed] == [first, second]  # l'ordre du programme
    one, two = listed
    assert (one["program_title"], one["week"], one["rank"]) == ("Parcours données", 1, 0)
    assert (two["week"], two["rank"], two["hours"], two["title"]) == (2, 0, 4, TITLE)
    assert one["hours"] is None and one["status"] == "brief_pending"
    assert one["skills"] == ["pandas", "Séries", "Index"] and two["skills"] == ["numpy"]
    assert {"module_id", "program_id", "validated_at", "profile_version", "session_id"} <= set(one)


async def test_portfolio_filters_by_status(env: Env, client: httpx.AsyncClient) -> None:
    await env.add_project(0, status="todo")
    done = await env.add_project(1, status="validated")
    assert [i["id"] for i in (await client.get(API, params={"status": "validated"})).json()] == [
        done
    ]
    assert (await client.get(API, params={"status": "inconnu"})).status_code == 422
    assert (await client.get(API, params={"status": "reviewing"})).json() == []


async def test_a_project_without_its_module_is_still_listed(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project(module_id="module-disparu", program_id="programme-disparu")
    [item] = (await client.get(API)).json()
    assert item["id"] == pid and item["week"] is None and item["program_title"] is None
    assert (await client.get(f"{API}/{pid}")).status_code == 200


async def test_project_has_brief_submissions_evaluation_and_drafts(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await AgentProjectStore(env.rt).save_review(env.user_id, "s1", pid, outcome())
    r = await submit(client, pid)  # un projet validé n'en accepte pas d'autre
    assert r.status_code == 409
    body = (await client.get(f"{API}/{pid}")).json()
    assert body["status"] == "validated" and body["title"] == TITLE and body["session_id"] is None
    assert body["brief"]["criteria"] == CRITERIA and body["brief"]["hours"] == 4
    assert body["brief"]["deliverable"] == "either"
    assert body["submissions"] == [
        {
            "at": body["submissions"][0]["at"],
            "repo_url": REPO_URL,
            "description": DESCRIPTION,
            "screenshots": 0,
        }
    ]
    evaluation = body["evaluation"]
    assert evaluation["verdict"] == "validated" and evaluation["repo_status"] == "read"
    assert evaluation["feedback"] == "Le retour du Praticien." and evaluation["at"]
    assert [
        (c["index"], c["criterion"], c["met"], c["comment"]) for c in evaluation["results"]
    ] == [(n, CRITERIA[n - 1], True, f"Commentaire {n}.") for n in range(1, 5)]
    assert [d["kind"] for d in body["drafts"]] == [
        "cv_line",
        "profile_entry",
        "linkedin_post",
        "readme_plan",
    ]
    assert body["validated_at"] and body["profile_version"] is None
    entry = body["drafts"][1]
    assert entry["entry"]["name"] == TITLE and entry["status"] == "ready" and not entry["edited"]


async def test_submissions_are_listed_last_first(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project()
    for text in ("Premier rendu", "Second rendu"):
        r = await submit(client, pid, data={"description": text}, files=shots(("a.png", PNG)))
        await env.launcher.end(env.user_id, r.json()["session_id"], "failed")
        await client.get(f"{API}/{pid}")
    shown = (await client.get(f"{API}/{pid}")).json()
    assert [s["description"] for s in shown["submissions"]] == ["Second rendu", "Premier rendu"]
    assert shown["status"] == "todo" and shown["submissions"][0]["screenshots"] == 1


async def test_screenshot_route_serves_image(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project()
    files = shots(("un.png", PNG), ("deux.png", JPEG), ("trois.jpg", WEBP))
    r = await submit(client, pid, files=files)
    assert r.status_code == 202
    for number, (data, media) in enumerate(
        [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")], start=1
    ):
        got = await client.get(f"{API}/{pid}/screenshots/{number}")
        assert got.status_code == 200 and got.content == data
        assert got.headers["content-type"] == media
        assert got.headers["cache-control"] == "no-store"
        assert got.headers["x-content-type-options"] == "nosniff"
        assert "filename" not in got.headers.get("content-disposition", "")
    assert (await client.get(f"{API}/{pid}/screenshots/4")).status_code == 404
    assert (await client.get(f"{API}/{pid}/screenshots/0")).status_code == 422
    assert (
        await client.get(f"{API}/{pid}/screenshots/1", params={"submission": 2})
    ).status_code == 404


async def test_older_submission_screenshots_stay_reachable(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project()
    first = await submit(client, pid, files=shots(("a.png", PNG)))
    await env.launcher.end(env.user_id, first.json()["session_id"], "failed")
    await client.get(f"{API}/{pid}")
    second = await submit(client, pid, files=shots(("b.jpg", JPEG)))
    assert second.status_code == 202
    assert (await client.get(f"{API}/{pid}/screenshots/1")).content == JPEG  # le dernier d'abord
    assert (await client.get(f"{API}/{pid}/screenshots/1", params={"submission": 2})).content == PNG


async def test_other_user_project_404(env: Env, client: httpx.AsyncClient) -> None:
    other = await env.add_project(user="autre-utilisatrice", submissions=[env.last_submission()])
    assert (await client.get(f"{API}/{other}")).status_code == 404
    assert (await submit(client, other)).status_code == 404
    assert (await client.get(f"{API}/{other}/screenshots/1")).status_code == 404
    assert (await client.post(f"{API}/{other}/brief")).status_code == 404
    assert (await client.get(f"{API}/inconnu")).json()["error"]["code"] == "project_not_found"
    assert (await client.get(API)).json() == []  # ni dans le Portfolio


async def test_journal_kind_project_returns_the_project_entry(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await AgentProjectStore(env.rt).save_review(env.user_id, "s-journal", pid, outcome())
    journal = (await client.get("/api/v1/journal", params={"kind": "project"})).json()
    [entry] = journal["entries"]
    assert (entry["kind"], entry["text"]) == ("project", f"Projet validé : {TITLE}")
    assert entry["occurred_on"] == "2026-11-24" and entry["links"]["session_id"] == "s-journal"
    others = (await client.get("/api/v1/journal", params={"kind": "quiz"})).json()
    assert others["entries"] == []
