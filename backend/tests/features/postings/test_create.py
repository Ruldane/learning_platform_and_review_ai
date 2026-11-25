"""`POST /postings` (D122) : texte collé ou lien lu dans la requête, idempotence sur le lien
normalisé et sur l'empreinte du texte (envois simultanés compris), 422 sans recopie, relance d'une
offre refusée ou interrompue, journaux sans lien, texte ni entreprise."""

import asyncio
import logging

import httpx
import pytest
from fastapi import FastAPI

from app.features.postings.repository import PostingRepository
from app.features.postings.schemas import PostingIn
from app.features.postings.service.create import _insert, source_of, text_digest
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import (
    API,
    LINK,
    count_postings,
    fresh,
    page,
    post_link,
)
from tests.support.memory import FakeWebReader


async def test_create_from_text_launches_gap_analysis(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    r = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created"] and body["session_id"]
    posting = body["posting"]
    assert launcher_spy.started == [("gap_analysis", {"posting_id": posting["id"]})]
    assert posting["source"] == "text" and posting["url"] is None
    assert posting["status"] == "analyzing" and posting["gap_session_id"] == body["session_id"]
    assert posting["text"] == POSTING_TEXT.strip() and posting["duplicates"] == []


async def test_same_text_twice_returns_existing(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    first = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    # Mêmes mots, autres blancs : même empreinte.
    again = await client.post(
        f"{API}/postings", json={"text": "  " + POSTING_TEXT.replace(" ", "  ")}
    )
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["created"] is False and again.json()["session_id"] is None
    assert again.json()["posting"]["id"] == first.json()["posting"]["id"]
    assert len(launcher_spy.started) == 1


async def test_same_link_twice_returns_existing(
    client: httpx.AsyncClient, app: FastAPI, fake_reader: FakeWebReader,
    launcher_spy: RecordingLauncher,
) -> None:  # fmt: skip
    fake_reader.pages[LINK] = page(LINK)
    first, again = await post_link(client), await post_link(client)
    assert (first.status_code, again.status_code) == (201, 200), again.text
    assert again.json()["posting"]["id"] == first.json()["posting"]["id"]
    assert again.json()["created"] is False and again.json()["session_id"] is None
    assert len(fake_reader.calls) == 1 and len(launcher_spy.started) == 1
    assert first.json()["posting"]["url"] == LINK and first.json()["posting"]["source"] == "url"


async def test_tracking_params_are_the_same_link(
    client: httpx.AsyncClient, fake_reader: FakeWebReader, launcher_spy: RecordingLauncher
) -> None:
    fake_reader.pages[LINK] = page(LINK)
    first = await post_link(client)
    again = await post_link(client, f"{LINK}/?utm_source=x&gclid=1#postuler")
    assert again.status_code == 200
    assert again.json()["posting"]["id"] == first.json()["posting"]["id"]


async def test_concurrent_same_link_creates_one(
    client: httpx.AsyncClient, app: FastAPI, fake_reader: FakeWebReader,
    launcher_spy: RecordingLauncher,
) -> None:  # fmt: skip
    fake_reader.pages[LINK] = page(LINK)
    a, b = await asyncio.gather(post_link(client), post_link(client))
    assert {a.status_code, b.status_code} == {200, 201}
    assert a.json()["posting"]["id"] == b.json()["posting"]["id"]
    assert await count_postings(app.state.session_factory) == 1
    assert len(launcher_spy.started) == 1


async def test_concurrent_same_text_creates_one(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    send = client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    again = client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    a, b = await asyncio.gather(send, again)
    assert {a.status_code, b.status_code} == {200, 201}
    assert a.json()["posting"]["id"] == b.json()["posting"]["id"]
    assert await count_postings(app.state.session_factory) == 1


@pytest.mark.parametrize("body", [{"url": LINK}, {"text": POSTING_TEXT}])
async def test_unique_index_race_reads_the_winner(
    client: httpx.AsyncClient, app: FastAPI, body: dict[str, str]
) -> None:
    """Le verrou par source contourné (second processus) : l'index unique tranche, la perdante
    relit la gagnante."""
    rt = app.state.career.postings
    source = source_of(PostingIn.model_validate(body))
    first = await _insert(rt, app.state.local_user_id, source, POSTING_TEXT)
    second = await _insert(rt, app.state.local_user_id, source, POSTING_TEXT)
    assert first[1] is True and second == (first[0], False)
    assert await count_postings(app.state.session_factory) == 1


async def test_unreadable_link_is_422_without_echo(
    client: httpx.AsyncClient, app: FastAPI, fake_reader: FakeWebReader,
    launcher_spy: RecordingLauncher,
) -> None:  # fmt: skip
    r = await client.post(f"{API}/postings", json={"url": "https://exemple.org/login"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "posting_unreadable"
    assert r.json()["error"]["message"] == (
        "This posting could not be read from its link. Paste the posting text instead."
    )
    assert r.json()["error"]["details"] == {"fields": ["url"]}
    assert "exemple.org" not in r.text and await count_postings(app.state.session_factory) == 0
    assert launcher_spy.started == []


@pytest.mark.parametrize(
    "link", ["https://exemple.org/#/offre/42", "https://exemple.org/#!/jobs/7"]
)
async def test_link_whose_route_is_in_the_fragment_is_never_read_at_the_root(
    client: httpx.AsyncClient, app: FastAPI, fake_reader: FakeWebReader,
    launcher_spy: RecordingLauncher, link: str,
) -> None:  # fmt: skip
    fake_reader.pages["https://exemple.org/"] = page("https://exemple.org/")  # la page d'accueil
    r = await client.post(f"{API}/postings", json={"url": link})
    assert r.status_code == 422 and r.json()["error"]["code"] == "posting_unreadable"
    assert r.json()["error"]["details"] == {"fields": ["url"]}
    assert "exemple.org" not in r.text and await count_postings(app.state.session_factory) == 0
    assert launcher_spy.started == []


async def test_a_plain_fragment_does_not_stop_the_reading(
    client: httpx.AsyncClient, app: FastAPI, fake_reader: FakeWebReader,
    launcher_spy: RecordingLauncher,
) -> None:  # fmt: skip
    fake_reader.pages[LINK] = page(LINK)
    r = await client.post(f"{API}/postings", json={"url": f"{LINK}#postuler"})
    assert r.status_code == 201, r.text


async def test_short_page_is_unreadable(
    client: httpx.AsyncClient, app: FastAPI, fake_reader: FakeWebReader
) -> None:
    fake_reader.pages[LINK] = page(LINK, "Offre courte. " * 8)  # 112 caractères
    r = await post_link(client)
    assert r.status_code == 422 and r.json()["error"]["code"] == "posting_unreadable"
    assert "Offre courte" not in r.text and await count_postings(app.state.session_factory) == 0


async def test_short_text_is_422_without_echo(client: httpx.AsyncClient, app: FastAPI) -> None:
    r = await client.post(f"{API}/postings", json={"text": "Poste secret chez Fictive SA."})
    assert r.status_code == 422 and r.json()["error"]["code"] == "posting_too_short"
    assert r.json()["error"]["message"] == "Posting text is too short. Paste the full posting."
    assert r.json()["error"]["details"] == {"fields": ["text"]}
    assert "secret" not in r.text and await count_postings(app.state.session_factory) == 0


async def test_both_or_none_source_is_422(client: httpx.AsyncClient) -> None:
    for body in ({}, {"text": "   "}, {"url": LINK, "text": POSTING_TEXT}, {"url": " "}):
        r = await client.post(f"{API}/postings", json=body)
        assert r.status_code == 422 and r.json()["error"]["code"] == "posting_source"
        assert r.json()["error"]["details"] == {"fields": ["url", "text"]}
        assert "Société Fictive" not in r.text and "jobs.exemple" not in r.text


async def test_bad_or_too_long_link_is_422_without_echo(client: httpx.AsyncClient) -> None:
    cases = {
        "file:///etc/secret": "invalid_url",
        "https://moi:motdepasse@exemple.org/offre": "url_forbidden",
        # Requête réencodée (« é » → « %C3%A9 ») : clé de plus de 2 048 caractères.
        "https://exemple.org/offre?q=" + "é" * 1000: "invalid_url",
    }
    for url, code in cases.items():
        r = await client.post(f"{API}/postings", json={"url": url})
        assert (r.status_code, r.json()["error"]["code"]) == (422, code), r.text
        assert "secret" not in r.text and "motdepasse" not in r.text and "%C3" not in r.text
    r = await client.post(f"{API}/postings", json={"text": "x" * 60_001})
    assert r.status_code == 422 and "xxxx" not in r.text


async def test_no_url_or_text_or_company_in_logs(
    client: httpx.AsyncClient, fake_reader: FakeWebReader, launcher_spy: RecordingLauncher,
    caplog: pytest.LogCaptureFixture,
) -> None:  # fmt: skip
    caplog.set_level(logging.DEBUG, logger="app")
    fake_reader.pages[LINK] = page(LINK)
    await post_link(client)
    await post_link(client)
    await client.post(f"{API}/postings", json={"url": "https://exemple.org/login"})
    await client.post(f"{API}/postings", json={"text": POSTING_TEXT + "\nAutre version."})
    assert caplog.records
    for needle in ("exemple.org", "AI Product Engineer", "Société Fictive", "LangGraph"):
        assert needle not in caplog.text


async def test_rejected_posting_is_relaunched_when_sent_again(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    first = (await client.post(f"{API}/postings", json={"text": POSTING_TEXT})).json()
    posting_id = first["posting"]["id"]
    await app.state.career.gap.reject(app.state.local_user_id, posting_id, "Pas une offre.")
    await launcher_spy.end(app.state.local_user_id, first["session_id"])
    again = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    assert again.status_code == 200 and again.json()["created"] is False
    assert again.json()["session_id"] not in (None, first["session_id"])
    row = await fresh(app.state.session_factory, posting_id)
    assert (row.status, row.failure_reason) == ("analyzing", None)
    assert row.gap_session_id == again.json()["session_id"] and len(launcher_spy.started) == 2


async def test_interrupted_analysis_is_shown_failed_then_relaunched(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    first = (await client.post(f"{API}/postings", json={"text": POSTING_TEXT})).json()
    posting_id = first["posting"]["id"]
    await launcher_spy.end(app.state.local_user_id, first["session_id"], "failed")
    shown = (await client.get(f"{API}/postings/{posting_id}")).json()
    assert shown["status"] == "failed" and shown["gap_session_id"] == first["session_id"]
    assert shown["failure_reason"] == "Posting analysis stopped. Restart the analysis."
    again = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    assert again.status_code == 200 and again.json()["session_id"] is not None
    assert again.json()["posting"]["status"] == "analyzing"


async def test_launch_failure_marks_posting_failed(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    launcher_spy.refuse = True
    r = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    assert (r.status_code, r.json()["error"]["code"]) == (503, "engine_unavailable")
    async with app.state.session_factory() as db:
        rows = await PostingRepository(db, app.state.local_user_id).list_recent()
    assert [(p.status, p.gap_session_id) for p in rows] == [("failed", None)]
    assert rows[0].text_hash == text_digest(POSTING_TEXT)
