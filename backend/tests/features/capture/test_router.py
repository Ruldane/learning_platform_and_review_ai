"""Routes de la capture et du journal (D108) : une seule source, lien http(s) seulement (422 sans
recopie), document d'une autre introuvable, `POST /sessions` renvoyé à la route, journal du plus
récent au plus ancien avec filtre et curseur, `data` jamais rendu, isolation des utilisateurs."""

from datetime import date

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.memory import Document
from app.features.capture.service.journal import JournalLinks, add_entry
from tests.features.lessons.conftest import RecordingLauncher

API = "/api/v1"
OTHER = "autre-utilisatrice"
DAY = date(2026, 11, 18)


@pytest.fixture
def launcher(app: FastAPI) -> RecordingLauncher:
    recording = RecordingLauncher(app.state.session_factory)
    app.state.capture.launcher = recording
    return recording


async def _document(app: FastAPI, user_id: str) -> str:
    async with app.state.session_factory() as db:
        doc = Document(
            user_id=user_id, name="notes.pdf", source_kind="pdf", status="queued",
            source_hash=f"src-{user_id}",
        )  # fmt: skip
        db.add(doc)
        await db.commit()
        return doc.id


async def _entries(app: FastAPI, user_id: str, *kinds: str) -> list[str]:
    ids = []
    async with app.state.session_factory() as db:
        for n, kind in enumerate(kinds):
            ids.append(
                await add_entry(
                    db, user_id, kind=kind, text=f"Ligne {n}", occurred_on=DAY,  # type: ignore[arg-type]
                    ref_key=f"k{n}", links=JournalLinks(session_id=f"s{n}"),
                    data={"secret": "donnée interne"},
                )
            )  # fmt: skip
            await db.commit()
    return ids


async def test_capture_starts_with_one_source(
    client: httpx.AsyncClient, app: FastAPI, launcher: RecordingLauncher
) -> None:
    doc = await _document(app, app.state.local_user_id)
    bodies = [
        {"url": "HTTPS://Blog.Exemple.org/attention#plan"},
        {"text": "  J'ai appris l'attention.  "},
        {"document_id": doc, "url": None},
    ]
    for body in bodies:
        r = await client.post(f"{API}/capture", json=body)
        assert r.status_code == 202, r.text
        assert set(r.json()) == {"session_id"}
    assert launcher.started == [
        ("capture", {"url": "https://blog.exemple.org/attention"}),
        ("capture", {"text": "J'ai appris l'attention."}),
        ("capture", {"document_id": doc}),
    ]


async def test_capture_requires_exactly_one_source(
    client: httpx.AsyncClient, launcher: RecordingLauncher
) -> None:
    for body in (
        {},
        {"text": "   "},
        {"url": "https://exemple.org/a", "text": "Une note."},
        {"text": "Une note.", "document_id": "d"},
    ):
        r = await client.post(f"{API}/capture", json=body)
        assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_input")
        assert "Une note" not in r.text
    assert launcher.started == []


async def test_capture_rejects_non_http_url_without_echo(
    client: httpx.AsyncClient, launcher: RecordingLauncher
) -> None:
    r = await client.post(f"{API}/capture", json={"url": "file:///etc/passwd"})
    assert r.status_code == 422 and "passwd" not in r.text
    assert r.json()["error"]["code"] == "invalid_url"
    for url in ("javascript:alert('secret')", "https://moi:motdepasse@exemple.org/x"):
        r = await client.post(f"{API}/capture", json={"url": url})
        assert r.status_code == 422 and "secret" not in r.text and "motdepasse" not in r.text
    long_text = "Mon journal intime " * 1100  # plus de 20 000 caractères
    r = await client.post(f"{API}/capture", json={"text": long_text})
    assert r.status_code == 422 and "intime" not in r.text
    assert launcher.started == []


async def test_sessions_route_refuses_capture(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{API}/sessions", json={"graph": "capture", "input": {"text": "x"}})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "graph_has_route")
    assert r.json()["error"]["details"] == {"graph": "capture", "route": "POST /capture"}


async def test_journal_lists_entries_newest_first_with_filter(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    ids = await _entries(
        app, app.state.local_user_id, "capture", "quiz", "capture", "weekly_review"
    )
    r = await client.get(f"{API}/journal")
    assert r.status_code == 200, r.text
    page = r.json()
    assert [e["id"] for e in page["entries"]] == ids[::-1] and page["next_before"] is None
    first = page["entries"][0]
    assert first == {
        "id": ids[3],
        "kind": "weekly_review",
        "text": "Ligne 3",
        "occurred_on": "2026-11-18",
        "created_at": first["created_at"],
        "links": {
            "session_id": "s3",
            "study_session_id": None,
            "quiz_attempt_id": None,
            "memory_item_id": None,
        },
    }
    assert "donnée interne" not in r.text  # `data` jamais exposé
    captures = (await client.get(f"{API}/journal", params={"kind": "capture"})).json()
    assert [e["id"] for e in captures["entries"]] == [ids[2], ids[0]]
    one = (await client.get(f"{API}/journal", params={"limit": 3})).json()
    assert [e["id"] for e in one["entries"]] == ids[:0:-1] and one["next_before"] == ids[1]
    rest = (await client.get(f"{API}/journal", params={"limit": 3, "before": ids[1]})).json()
    assert [e["id"] for e in rest["entries"]] == [ids[0]] and rest["next_before"] is None
    for params in ({"limit": 0}, {"limit": 101}, {"kind": "secret_kind"}):
        bad = await client.get(f"{API}/journal", params=params)
        assert bad.status_code == 422 and "secret_kind" not in bad.text


async def test_capture_and_journal_isolate_users(
    client: httpx.AsyncClient, app: FastAPI, launcher: RecordingLauncher
) -> None:
    theirs = await _document(app, OTHER)
    r = await client.post(f"{API}/capture", json={"document_id": theirs})
    assert (r.status_code, r.json()["error"]["code"]) == (404, "document_not_found")
    assert launcher.started == []
    their_entries = await _entries(app, OTHER, "capture")
    mine = await _entries(app, app.state.local_user_id, "quiz")
    listed = (await client.get(f"{API}/journal")).json()
    assert [e["id"] for e in listed["entries"]] == mine
    r = await client.get(f"{API}/journal", params={"before": their_entries[0]})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_cursor")
