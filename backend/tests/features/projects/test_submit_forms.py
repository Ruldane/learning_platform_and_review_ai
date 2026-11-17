"""Rendre un projet, suite (D166) : deux rendus simultanés, type annoncé jamais cru, signatures
tronquées, champs de formulaire hors norme (422, jamais une erreur d'analyse), statut corrigé qui ne
double pas l'événement du fil."""

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.features.projects.service.screenshots import detect_image
from tests.features.projects.support import API, JPEG, NOW, PNG, Env, shots, stored, submit


async def test_two_simultaneous_submits_give_one_202_and_one_409(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    first, second = await asyncio.gather(
        submit(client, pid, files=shots(("a.png", PNG), ("b.jpg", JPEG))),
        submit(client, pid, files=shots(("c.png", PNG), ("d.jpg", JPEG))),
    )
    assert sorted([first.status_code, second.status_code]) == [202, 409]
    won, lost = (first, second) if first.status_code == 202 else (second, first)
    error = lost.json()["error"]
    assert error["code"] == "review_in_progress"
    assert error["details"] == {"session_id": won.json()["session_id"]}
    assert len(env.launcher.started) == 1  # une seule session
    row = await env.row(pid)
    assert len(row.submissions) == 1 and row.session_id == won.json()["session_id"]
    assert len(stored(tmp_path, env.user_id)) == 2  # un seul jeu de captures rangé


async def test_the_announced_type_is_never_trusted(
    env: Env, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    pid = await env.add_project()
    text = b"ce n'est pas une image du tout"
    for announced in ("image/png", "image/jpeg", "image/webp"):
        r = await submit(client, pid, files=shots(("photo.png", text, announced)))
        assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["screenshots"]}
    assert not stored(tmp_path, env.user_id) and not env.launcher.started
    real = await submit(client, pid, files=shots(("x.bin", PNG, "text/plain")))
    assert real.status_code == 202  # les octets font foi, pas le type annoncé


@pytest.mark.parametrize(
    "data",
    [
        b"\xff\xd8\xff",
        b"\xff\xd8\xff\x00",
        b"\xff\xd8\xff\xff",
        b"\xff\xd8\xff\xe0",  # le JPEG nu de 4 octets (D181)
        b"\xff\xd8",
        b"\x89PNG",
        b"RIFF",
    ],
)
async def test_a_truncated_signature_is_not_an_image(
    env: Env, client: httpx.AsyncClient, data: bytes
) -> None:
    pid = await env.add_project()
    r = await submit(client, pid, files=shots(("t.jpg", data, "image/jpeg")))
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["screenshots"]}


async def test_jpeg_with_a_marker_after_the_signature_is_accepted(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project()
    for marker in (b"\xe0", b"\xdb", b"\xc0", b"\xfe"):
        data = b"\xff\xd8\xff" + marker + b"suite"
        assert detect_image(data) == "image/jpeg"
    r = await submit(client, pid, files=shots(("t.jpg", b"\xff\xd8\xff\xe1" + b"x" * 20)))
    assert r.status_code == 202


async def test_a_text_field_over_one_megabyte_is_422_not_a_parse_error(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project()
    r = await client.post(
        f"{API}/{pid}/submit",
        data={"description": "mot-secret " * 120_000},  # plus de 1 Mo : limite de Starlette
        files=shots(("a.png", PNG)),
    )
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["description"]}
    assert "mot-secret" not in r.text
    assert not env.launcher.started and (await env.row(pid)).submissions == []


async def test_a_text_value_in_the_screenshots_field_is_422(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project()
    for body in (
        {"description": "Un texte", "screenshots": "valeur-secrete"},
        {"description": "Un texte", "screenshots": ["valeur-secrete", "autre"]},
    ):
        r = await client.post(f"{API}/{pid}/submit", data=body)
        assert r.status_code == 422, r.text
        fields = r.json()["error"]["details"]["fields"]
        assert fields and all(field.startswith("screenshots") for field in fields)
        assert "valeur-secrete" not in r.text
    assert not env.launcher.started


async def project_events(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get("/api/v1/activity")).json()["items"]
    return [item for item in items if item["kind"] == "project"]


async def test_settling_a_dead_review_does_not_duplicate_the_feed_event(
    env: Env, client: httpx.AsyncClient
) -> None:
    evaluation = {
        "session_id": "s-ancienne",
        "at": NOW.isoformat(),
        "verdict": "to_redo",
        "results": [],
        "feedback": "x",
        "repo_status": "read",
    }
    pid = await env.add_project(
        status="to_redo", submissions=[env.last_submission()], evaluation=evaluation
    )
    [event] = await project_events(client)
    sid = (await submit(client, pid)).json()["session_id"]
    assert await project_events(client) == []  # rendu en cours
    await env.launcher.end(env.user_id, sid, "failed")
    assert (await client.get(f"{API}/{pid}")).json()["status"] == "to_redo"  # `settle`
    assert await project_events(client) == [event]  # même identifiant, même instant
    newer = await client.get(
        "/api/v1/activity", params={"after": event["at"], "after_id": event["id"]}
    )
    assert [i for i in newer.json()["items"] if i["kind"] == "project"] == []
