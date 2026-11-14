"""Routes des offres (D122) : liste (plus récentes d'abord, score et revue), détail avec analyse et
doublons relus, suppression avec l'élément `offre` (409 si une revue tourne), « offres
distinctes », relance de l'analyse (409 si elle tourne), isolation des utilisateurs, et
`POST /sessions` renvoyé à la route."""

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select

from app.agents.tools.gap_port import SkillMatch
from app.db.models.career import CvReview
from app.db.models.memory import MemoryItem
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import API, analysis
from tests.sessions_support import act_as
from tests.support.gap import MATCHES

OTHER_TEXT = POSTING_TEXT + "\nPoste ouvert aux profils juniors."


async def _create(client: httpx.AsyncClient, text: str = POSTING_TEXT) -> dict[str, str]:
    r = await client.post(f"{API}/postings", json={"text": text})
    assert r.status_code == 201, r.text
    return {"id": r.json()["posting"]["id"], "session": r.json()["session_id"]}


async def _analyze(app: FastAPI, created: dict[str, str], **over: object) -> None:
    store, user = app.state.career.gap, app.state.local_user_id
    await store.save_analysis(user, created["session"], created["id"], analysis(**over))
    found = [SkillMatch(need=n, known=k) for n, k in MATCHES.items()]
    await store.save_gap(user, created["session"], created["id"], found)


async def test_list_and_detail(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    first = await _create(client)
    second = await _create(client, OTHER_TEXT)
    await _analyze(app, first)
    listed = (await client.get(f"{API}/postings")).json()
    assert [p["id"] for p in listed] == [second["id"], first["id"]]
    assert listed[1] == {
        "id": first["id"],
        "title": "AI Product Engineer",
        "company": "Société Fictive",
        "status": "ready",
        "source": "text",
        "score": 0,  # aucune compétence au référentiel
        "created_at": listed[1]["created_at"],
        "has_review": False,
    }
    assert listed[0]["score"] is None and listed[0]["status"] == "analyzing"
    detail = (await client.get(f"{API}/postings/{first['id']}")).json()
    assert detail["analysis"]["title"] == "AI Product Engineer"
    assert detail["analysis"]["skills"][0] == {
        "name": "Python", "required": True, "domain": None, "learnable": True,
    }  # fmt: skip
    assert "is_job_posting" not in detail["analysis"] and detail["text"] == POSTING_TEXT.strip()


async def test_duplicates_are_shown_after_analysis(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    first, second = await _create(client), await _create(client, OTHER_TEXT)
    await _analyze(app, first)
    await _analyze(app, second, title="Product Engineer AI")
    shown = (await client.get(f"{API}/postings/{second['id']}")).json()["duplicates"]
    assert [(d["level"], d["posting_id"], d["title"]) for d in shown] == [
        ("probable", first["id"], "AI Product Engineer")
    ]
    assert shown[0]["created_at"].endswith("+01:00")


async def test_distinct_hides_duplicate_both_ways(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    first, second = await _create(client), await _create(client, OTHER_TEXT)
    await _analyze(app, first)
    await _analyze(app, second, title="Product Engineer AI")
    r = await client.post(f"{API}/postings/{first['id']}/distinct", json={"other_id": second["id"]})
    assert r.status_code == 204
    for one in (first, second):
        assert (await client.get(f"{API}/postings/{one['id']}")).json()["duplicates"] == []
    r = await client.post(f"{API}/postings/{first['id']}/distinct", json={"other_id": "nope"})
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")


async def _items(app: FastAPI) -> int:
    async with app.state.session_factory() as db:
        return int((await db.execute(select(func.count()).select_from(MemoryItem))).scalar_one())


async def test_delete_removes_memory_item(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    await _analyze(app, created)
    await launcher_spy.end(app.state.local_user_id, created["session"])  # l'analyse est finie
    assert await _items(app) == 1
    r = await client.delete(f"{API}/postings/{created['id']}")
    assert r.status_code == 204
    assert await _items(app) == 0
    r = await client.get(f"{API}/postings/{created['id']}")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")


async def test_delete_refused_while_a_review_runs(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    async with app.state.session_factory() as db:
        db.add(
            CvReview(
                user_id=app.state.local_user_id, posting_id=created["id"], template_id="t",
                profile_version=1, status="running",
            )
        )  # fmt: skip
        await db.commit()
    r = await client.delete(f"{API}/postings/{created['id']}")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_in_progress")
    assert (await client.get(f"{API}/postings")).json()[0]["has_review"] is True


async def test_relaunch_gap(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    r = await client.post(f"{API}/postings/{created['id']}/gap")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "gap_in_progress")
    await launcher_spy.end(app.state.local_user_id, created["session"], "failed")
    r = await client.post(f"{API}/postings/{created['id']}/gap")
    assert r.status_code == 202 and r.json()["session_id"] != created["session"]
    detail = (await client.get(f"{API}/postings/{created['id']}")).json()
    assert (detail["status"], detail["gap_session_id"]) == ("analyzing", r.json()["session_id"])
    assert [g for g, _ in launcher_spy.started] == ["gap_analysis", "gap_analysis"]


async def test_other_user_posting_is_404(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    act_as(app, "autre-utilisatrice")
    for method, path in (
        ("GET", f"/postings/{created['id']}"),
        ("GET", f"/postings/{created['id']}/gap"),
        ("DELETE", f"/postings/{created['id']}"),
        ("POST", f"/postings/{created['id']}/gap"),
    ):
        r = await client.request(method, f"{API}{path}")
        assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found"), path
    assert (await client.get(f"{API}/postings")).json() == []
    # Le même texte chez une autre : une offre à elle.
    r = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    assert r.status_code == 201 and r.json()["posting"]["id"] != created["id"]


async def test_sessions_route_refuses_gap_analysis(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"{API}/sessions", json={"graph": "gap_analysis", "input": {"posting_id": "x" * 36}}
    )
    assert (r.status_code, r.json()["error"]["code"]) == (409, "graph_has_route")
    assert r.json()["error"]["details"]["route"] == "POST /postings"
