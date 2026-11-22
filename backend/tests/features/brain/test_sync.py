"""Synchronisation Cerveau : cycle de vie réel des documents avec fournisseurs factices."""

from hashlib import sha256

import httpx
import pytest
from fastapi import FastAPI

API = "/api/v1"
BRAIN = f"{API}/brain"
SYNC = f"{BRAIN}/sync/folders"
CONFIGURED_PATH = "C:/chemin-fictif/coffre"
FIRST = b"---\ntags: [projet]\n---\nUne ancienne note de test sur les reptiles. [[Autre note]]\n"
SECOND = "Une nouvelle note fictive sur l'océan Pacifique.".encode()


async def configure(client: httpx.AsyncClient) -> tuple[dict[str, object], str]:
    folder = await client.post(f"{BRAIN}/folders", json={"name": "Notes", "path": CONFIGURED_PATH})
    assert folder.status_code == 201, folder.text
    token = await client.post(f"{BRAIN}/sync-token")
    assert token.status_code in (200, 201), token.text
    return folder.json(), token.json()["token"]


def auth(token: str, revision: object = 1) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tremplin-Folder-Revision": str(revision)}


async def upload(
    client: httpx.AsyncClient,
    folder: dict[str, object],
    token: str,
    content: bytes,
    path: str = "notes/note.md",
    digest: str | None = None,
) -> httpx.Response:
    return await client.post(
        f"{SYNC}/{folder['id']}/files",
        headers=auth(token, folder["revision"]),
        data={"path": path, "sha256": digest or sha256(content).hexdigest()},
        files={"file": ("nom-recu-inutilise.md", content, "text/plain")},
    )


async def memory_items(client: httpx.AsyncClient) -> list[dict[str, object]]:
    result = await client.get(f"{API}/memory/items", params={"kind": "document"})
    assert result.status_code == 200, result.text
    return result.json()["items"]


async def test_sync_replaces_and_removes_visible_document_fragments(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    folder, token = await configure(client)
    wrote = await upload(client, folder, token, FIRST)
    assert wrote.status_code in (200, 202), wrote.text
    await app.state.memory.jobs.join()
    [before] = await memory_items(client)
    assert "reptiles" in before["text"] and before["tags"] == ["projet"]
    scope = f"{SYNC}/{folder['id']}"
    response = await client.get(f"{scope}/inventory", headers=auth(token))
    [entry] = response.json()["files"]
    assert entry["status"] == "indexed" and entry["path"] == "notes/note.md"

    repeated = await upload(client, folder, token, FIRST)
    assert repeated.json()["document_id"] == entry["document_id"]
    changed = await upload(client, folder, token, SECOND)
    assert changed.status_code in (200, 202), changed.text
    await app.state.memory.jobs.join()
    [after] = await memory_items(client)
    assert "Pacifique" in after["text"] and "reptiles" not in after["text"]
    stale = await client.post(f"{API}/memory/search", json={"query": "reptiles"})
    assert all("reptiles" not in hit["text"] for hit in stale.json()["hits"])

    for _ in range(2):
        removed = await client.post(
            f"{scope}/remove", headers=auth(token), json={"path": "notes/note.md"}
        )
        assert removed.status_code == 204, removed.text
    assert await memory_items(client) == []


async def test_copies_at_different_paths_have_independent_documents(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    folder, token = await configure(client)
    first = await upload(client, folder, token, FIRST, "une/note.md")
    other = await upload(client, folder, token, FIRST, "deux/note.md")
    assert first.json()["document_id"] != other.json()["document_id"]
    await app.state.memory.jobs.join()
    assert len(await memory_items(client)) == 2


async def test_interrupt_before_enqueue_is_recovered_from_the_persistent_inventory(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, token = await configure(client)
    jobs = app.state.memory.jobs
    with monkeypatch.context() as patch:
        patch.setattr(jobs, "enqueue_ingest", lambda *_: None)
        response = await upload(client, folder, token, FIRST)
    assert response.status_code == 202
    [entry] = (await client.get(f"{SYNC}/{folder['id']}/inventory", headers=auth(token))).json()[
        "files"
    ]
    assert entry["status"] == "queued" and await memory_items(client) == []

    await jobs.aclose()
    await jobs.start()
    await jobs.join()
    again = await upload(client, folder, token, FIRST)
    assert again.json()["status"] == "indexed"
    assert again.json()["document_id"] == entry["document_id"]
    assert len(await memory_items(client)) == 1


async def test_folder_report_hides_paths_and_is_cleared_when_replacing_the_root(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    folder, token = await configure(client)
    first = await upload(client, folder, token, FIRST)
    assert first.status_code == 202
    await app.state.memory.jobs.join()
    scope = f"{SYNC}/{folder['id']}"
    data = {
        "state": "done",
        "scanned": 1,
        "added": 1,
        "changed": 0,
        "removed": 0,
        "ignored": {"tooLarge": 2, "technical": 1, "chemin-fictif": 4},
        "errors": 0,
    }
    report = await client.post(f"{scope}/report", headers=auth(token), json=data)
    assert report.status_code == 204, report.text
    status = await client.get(f"{BRAIN}/status")
    [row] = status.json()
    assert row["total"] == row["indexed"] == 1 and row["report"]["reported_at"]
    assert row["report"]["ignored"]["tooLarge"] == 2
    assert "chemin-fictif" not in status.text and "note.md" not in status.text

    path = f"{BRAIN}/folders/{folder['id']}"
    replaced = await client.patch(path, json={"path": "C:/chemin-fictif/nouveau"})
    assert replaced.status_code == 200 and replaced.json()["revision"] == 2
    assert await memory_items(client) == []
    assert (await client.get(f"{scope}/inventory", headers=auth(token, 2))).json()["files"] == []
    assert (await client.get(f"{BRAIN}/status")).json()[0]["report"] is None
    assert (await client.delete(path)).status_code == 204
    assert (await client.get(SYNC, headers=auth(token))).json() == []


@pytest.mark.parametrize(
    "path", ["../faux-secret.md", ".obsidian/faux-secret.md", "C:/faux-secret.md"]
)
async def test_invalid_relative_path_is_refused_without_echo(
    client: httpx.AsyncClient, path: str
) -> None:
    folder, token = await configure(client)
    response = await upload(client, folder, token, FIRST, path)
    assert response.status_code == 422 and response.json()["error"]["code"] == "brain_path_invalid"
    assert "faux-secret" not in response.text


async def test_enforces_upload_hash_type_and_size(client: httpx.AsyncClient) -> None:
    folder, token = await configure(client)
    invalid_hash = await upload(client, folder, token, FIRST, digest="0" * 64)
    assert invalid_hash.status_code == 422 and "brain_digest_mismatch" in invalid_hash.text
    disguised = await upload(client, folder, token, b"\x00\x01\x02", "faux-binaire.md")
    assert disguised.status_code == 415 and "faux-binaire" not in disguised.text
    large = await upload(client, folder, token, b"x" * (20 * 1024 * 1024 + 1))
    assert large.status_code == 413 and "file_too_large" in large.text
