"""Rendre un projet (P2, D166) : lien et/ou description, cinq captures au plus vérifiées par leurs
octets de tête, 422 sans écho, 409 (énoncé absent, évaluation en cours, projet validé), 413, le
statut qui suit la session (échec, annulation, fin sans évaluation : January peut rendre de
nouveau), lancement refusé."""

from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from app.features.projects.service.submit import MAX_SUBMISSIONS
from tests.features.ide.mcp_support import acting_as_claude
from tests.features.projects.support import (
    API,
    JPEG,
    NOW,
    PNG,
    WEBP,
    Env,
    shots,
    stored,
    submit,
)
from tests.support.projects import DESCRIPTION, REPO_URL


async def test_submit_202_and_review_in_progress_409(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, files=shots(("a.png", PNG), ("b.jpg", JPEG)))
    assert r.status_code == 202
    session_id = r.json()["session_id"]
    assert env.launcher.started == [("project_review", {"project_id": pid})]
    row = await env.row(pid)
    assert (row.status, row.session_id) == ("reviewing", session_id)
    [sub] = row.submissions
    assert (sub["repo_url"], sub["description"], len(sub["screenshots"])) == (
        REPO_URL,
        DESCRIPTION,
        2,
    )
    again = await submit(client, pid)
    assert again.status_code == 409
    error = again.json()["error"]
    assert error["code"] == "review_in_progress" and error["details"] == {"session_id": session_id}
    assert len(env.launcher.started) == 1 and len((await env.row(pid)).submissions) == 1
    shown = (await client.get(f"{API}/{pid}")).json()
    assert shown["status"] == "reviewing" and shown["session_id"] == session_id
    assert shown["submissions"][0]["screenshots"] == 2


async def test_submit_before_the_brief_is_409(env: Env, client: httpx.AsyncClient) -> None:
    for module, status in enumerate(("brief_pending", "brief_failed")):
        pid = await env.add_project(module, status=status, brief=False)
        r = await submit(client, pid)
        assert r.status_code == 409 and r.json()["error"]["code"] == "project_not_ready"
    assert not env.launcher.started


async def test_submit_only_screenshots_is_422(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, data={}, files=shots(("secret-capture.png", PNG)))
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["repo_url", "description"]}
    assert "secret-capture" not in r.text
    assert not env.launcher.started and not stored(tmp_path, env.user_id)
    assert (await env.row(pid)).status == "todo"


async def test_fake_png_is_422(env: Env, client: httpx.AsyncClient, tmp_path: Path) -> None:
    pid = await env.add_project()
    fake = b"ceci n'est pas une image, malgre l'extension"
    r = await submit(client, pid, files=shots(("photo.png", fake)))
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["screenshots"]}
    assert "photo.png" not in r.text and "ceci n'est pas" not in r.text
    assert not stored(tmp_path, env.user_id) and not env.launcher.started
    assert (await env.row(pid)).submissions == []
    # un fichier vide n'est pas une image non plus
    assert (await submit(client, pid, files=shots(("vide.png", b"")))).status_code == 422


async def test_good_and_bad_screenshots_together_store_nothing(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, files=shots(("a.png", PNG), ("b.png", b"texte")))
    assert r.status_code == 422 and not stored(tmp_path, env.user_id)


@pytest.mark.parametrize(
    ("link", "ok"),
    [
        ("ftp://example.org/depot", False),
        ("javascript:alert(1)", False),
        ("https://example.org/" + "a" * 2040, False),  # plus de 2 048 caractères
        ("https://example.org/" + "a" * 2000, True),
    ],
)
async def test_repo_url_is_http_and_capped(
    env: Env, client: httpx.AsyncClient, link: str, ok: bool
) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, data={"repo_url": link, "description": "Un texte"})
    if ok:
        assert r.status_code == 202
    else:
        assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["repo_url"]}
        assert link[:30] not in r.text


async def test_a_long_description_is_422_without_echo(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, data={"description": "mot-secret " * 500})
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["description"]}
    assert "mot-secret" not in r.text


async def test_six_screenshots_are_422(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, files=shots(*[(f"{n}.png", PNG) for n in range(6)]))
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["screenshots"]}
    five = await submit(client, pid, files=shots(*[(f"{n}.png", PNG) for n in range(5)]))
    assert five.status_code == 202


async def test_screenshot_over_five_megabytes_is_413(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project()
    big = PNG + b"\x00" * (5 * 1024 * 1024)
    r = await submit(client, pid, files=shots(("grande.png", big)))
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"
    assert "grande" not in r.text and not env.launcher.started


async def test_body_over_the_limit_is_413_before_reading(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project()
    body = b"x" * (5 * 5 * 1024 * 1024 + 1024 * 1024 + 1)
    r = await client.post(
        f"{API}/{pid}/submit", content=body, headers={"content-type": "multipart/form-data"}
    )
    assert r.status_code == 413 and "Rendu trop volumineux" in r.json()["error"]["message"]


async def test_stored_suffix_comes_from_the_detected_type_not_the_filename(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    files = shots(("secret.exe", PNG), ("autre.png", JPEG), ("troisieme.txt", WEBP))
    assert (await submit(client, pid, files=files)).status_code == 202
    assert [path.suffix for path in stored(tmp_path, env.user_id)].count(".png") == 1
    [sub] = (await env.row(pid)).submissions
    assert [key.rsplit(".", 1)[1] for key in sub["screenshots"]] == ["png", "jpg", "webp"]
    assert not any(
        "secret" in path.name or "autre" in path.name for path in stored(tmp_path, env.user_id)
    )


async def test_validated_project_refuses_resubmit(env: Env, client: httpx.AsyncClient) -> None:
    pid = await env.add_project(status="validated", submissions=[env.last_submission()])
    r = await submit(client, pid)
    assert r.status_code == 409 and r.json()["error"]["code"] == "project_validated"
    assert not env.launcher.started and len((await env.row(pid)).submissions) == 1


async def test_refused_launch_removes_the_submission_and_says_503(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    env.launcher.refuse = True
    r = await submit(client, pid, files=shots(("a.png", PNG)))
    assert r.status_code == 503 and r.json()["error"]["code"] == "review_unavailable"
    row = await env.row(pid)
    assert (row.status, row.submissions, row.session_id) == ("todo", [], None)
    assert not stored(tmp_path, env.user_id)
    env.launcher.refuse = False
    assert (await submit(client, pid)).status_code == 202  # January peut rendre de nouveau


async def test_refused_launch_of_a_second_try_restores_to_redo(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project(
        status="to_redo",
        submissions=[env.last_submission()],
        evaluation={"verdict": "to_redo", "results": [], "feedback": "x", "repo_status": "read"},
    )
    env.launcher.refuse = True
    assert (await submit(client, pid)).status_code == 503
    row = await env.row(pid)
    assert row.status == "to_redo" and len(row.submissions) == 1


@pytest.mark.parametrize("ending", ["failed", "cancelled", "completed"])
async def test_status_follows_the_session_so_january_can_resubmit(
    env: Env, client: httpx.AsyncClient, ending: str
) -> None:
    pid = await env.add_project()
    sid = (await submit(client, pid)).json()["session_id"]
    assert (await client.get(f"{API}/{pid}")).json()["status"] == "reviewing"
    await env.launcher.end(env.user_id, sid, ending)
    shown = (await client.get(f"{API}/{pid}")).json()
    assert shown["status"] == "todo" and shown["session_id"] is None
    assert shown["evaluation"] is None and len(shown["submissions"]) == 1
    again = await submit(client, pid, data={"description": "Un second rendu"})
    assert again.status_code == 202 and again.json()["session_id"] != sid
    assert len((await env.row(pid)).submissions) == 2


async def test_a_dead_review_of_a_second_try_goes_back_to_to_redo(
    env: Env, client: httpx.AsyncClient
) -> None:
    evaluation = {"verdict": "to_redo", "results": [], "feedback": "x", "repo_status": "read"}
    pid = await env.add_project(
        status="to_redo", submissions=[env.last_submission()], evaluation=evaluation
    )
    sid = (await submit(client, pid)).json()["session_id"]
    await env.launcher.end(env.user_id, sid, "failed")
    listed = (await client.get(API)).json()
    assert [item["status"] for item in listed] == ["to_redo"]


async def test_a_review_without_a_session_past_the_grace_goes_back(
    env: Env, client: httpx.AsyncClient
) -> None:
    old = NOW - timedelta(minutes=10)
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await env.patch(pid, updated_at=old, session_id=None)
    assert (await client.get(f"{API}/{pid}")).json()["status"] == "todo"
    fresh = await env.add_project(1, status="reviewing", submissions=[env.last_submission()])
    await env.patch(fresh, updated_at=NOW - timedelta(minutes=1), session_id=None)
    assert (await client.get(f"{API}/{fresh}")).json()[
        "status"
    ] == "reviewing"  # en cours de lancement


async def test_only_the_last_ten_submissions_are_kept(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    for number in range(MAX_SUBMISSIONS + 1):
        r = await submit(
            client,
            pid,
            data={"description": f"Rendu numéro {number}"},
            files=shots((f"{number}.png", PNG)),
        )
        assert r.status_code == 202, r.text
        await env.launcher.end(env.user_id, r.json()["session_id"], "failed")
        await client.get(f"{API}/{pid}")  # le statut suit la session
    row = await env.row(pid)
    assert len(row.submissions) == MAX_SUBMISSIONS
    assert row.submissions[0]["description"] == "Rendu numéro 1"  # le plus ancien est parti
    assert len(stored(tmp_path, env.user_id)) == MAX_SUBMISSIONS  # et sa capture avec lui


async def test_refused_launch_keeps_the_oldest_submission_of_a_full_list(
    env: Env, client: httpx.AsyncClient
) -> None:
    older = [{**env.last_submission(), "description": f"Rendu {n}"} for n in range(MAX_SUBMISSIONS)]
    pid = await env.add_project(submissions=older)
    env.launcher.refuse = True
    assert (await submit(client, pid)).status_code == 503
    assert [s["description"] for s in (await env.row(pid)).submissions] == [
        f"Rendu {n}" for n in range(MAX_SUBMISSIONS)
    ]


async def test_claude_cannot_submit_a_project(env: Env, client: httpx.AsyncClient) -> None:
    """10.R (I1) : rendre un projet est un geste de January ; sous identité MCP, 403 et rien n'est
    évalué ni rendu."""
    pid = await env.add_project()
    with acting_as_claude(env.user_id):
        refused = await submit(client, pid)
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "mcp_gesture_forbidden"
    row = await env.row(pid)
    assert (row.status, row.submissions, row.session_id) == ("todo", [], None)
    assert not env.launcher.started
    assert (await submit(client, pid)).status_code == 202
