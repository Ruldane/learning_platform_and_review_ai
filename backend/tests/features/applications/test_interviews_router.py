"""Routes des entretiens blancs (D146) : lancement depuis une fiche ou libre (202, 409, 404, 422),
liste et détail, statut qui suit la session, journaux sans donnée personnelle et isolation."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete

from app.db.models.career import MasterProfile
from tests.features.applications.conftest import add_posting
from tests.features.applications.interview_support import (
    BODY,
    ROOT,
    add_profile,
    interview_row,
    launch,
    ready_application,
    running_application,
    save_done,
    spy,
)

pytestmark = pytest.mark.usefixtures("client")
UNKNOWN = "00000000-0000-4000-8000-000000000000"


async def test_launch_from_application(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    application_id = await ready_application(client, app)
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert r.status_code == 202, r.text
    started = r.json()
    assert set(started) == {"interview_id", "session_id"}
    assert launcher.started == [("interview", {"interview_id": started["interview_id"]})]
    view = (await client.get(f"{ROOT}/sessions/{started['session_id']}")).json()
    assert (view["graph"], view["subject_type"], view["subject_id"]) == (
        "interview",
        "interview",
        started["interview_id"],
    )
    got = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert (got["mode"], got["duration_min"], got["language"], got["status"]) == (
        "behavioral",
        30,
        "fr",
        "running",
    )
    assert (got["application_id"], got["session_id"]) == (application_id, started["session_id"])
    assert (got["exchanges"], got["debrief"], got["flags"], got["cards_created"]) == (
        [],
        None,
        [],
        0,
    )
    row = await interview_row(app, started["interview_id"])
    assert row.role == "Développeuse IA" and row.session_id == started["session_id"]


async def test_language_defaults_to_english(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    r = await client.post(
        f"{ROOT}/applications/{application_id}/interviews",
        json={"mode": "case", "duration_min": 15},
    )
    assert r.status_code == 202
    got = (await client.get(f"{ROOT}/interviews/{r.json()['interview_id']}")).json()
    assert (got["mode"], got["duration_min"], got["language"]) == ("case", 15, "en")


async def test_free_interview_on_role(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    await add_profile(app)
    r = await client.post(f"{ROOT}/interviews", json=BODY | {"role": "Data engineer"})
    assert r.status_code == 202, r.text
    got = (await client.get(f"{ROOT}/interviews/{r.json()['interview_id']}")).json()
    assert (got["role"], got["application_id"], got["posting_id"]) == ("Data engineer", None, None)
    assert launcher.started == [("interview", {"interview_id": r.json()["interview_id"]})]


async def test_free_interview_on_posting(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    await add_profile(app)
    posting_id = await add_posting(app, title="Ingénieure agents")
    r = await client.post(f"{ROOT}/interviews", json=BODY | {"posting_id": posting_id})
    assert r.status_code == 202, r.text
    got = (await client.get(f"{ROOT}/interviews/{r.json()['interview_id']}")).json()
    assert (got["posting_id"], got["role"]) == (posting_id, "Ingénieure agents")
    missing = await client.post(f"{ROOT}/interviews", json=BODY | {"posting_id": UNKNOWN})
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "posting_not_found")


async def test_second_running_is_409(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    application_id, first = await running_application(client, app)
    again = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "interview_in_progress")
    assert again.json()["error"]["details"] == {"interview_id": first["interview_id"]}
    free = await client.post(f"{ROOT}/interviews", json=BODY | {"role": "Autre poste"})
    assert (free.status_code, free.json()["error"]["code"]) == (409, "interview_in_progress")
    assert len(launcher.started) == 1
    # Une fois la session finie, un autre entretien peut partir.
    await launcher.end(str(app.state.local_user_id), first["session_id"], "cancelled")
    second = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert second.status_code == 202
    assert second.json()["interview_id"] != first["interview_id"]


async def test_launch_needs_a_profile(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    application_id = await ready_application(client, app)
    async with app.state.session_factory() as db:
        await db.execute(delete(MasterProfile))
        await db.commit()
    for url, body in (
        (f"{ROOT}/applications/{application_id}/interviews", BODY),
        (f"{ROOT}/interviews", BODY | {"role": "Poste"}),
    ):
        r = await client.post(url, json=body)
        assert (r.status_code, r.json()["error"]["code"]) == (409, "profile_required")
    assert launcher.started == []
    assert (await client.get(f"{ROOT}/interviews")).json() == []


async def test_launch_when_the_engine_is_down(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    launcher.refuse = True
    application_id = await ready_application(client, app)
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert (r.status_code, r.json()["error"]["code"]) == (503, "engine_unavailable")
    [row] = (await client.get(f"{ROOT}/interviews")).json()
    assert row["status"] == "failed"
    launcher.refuse = False
    again = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert again.status_code == 202


async def test_launch_unknown_application_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    await add_profile(app)
    r = await client.post(f"{ROOT}/applications/{UNKNOWN}/interviews", json=BODY)
    assert (r.status_code, r.json()["error"]["code"]) == (404, "application_not_found")
    assert launcher.started == []


async def test_422_no_echo(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    secret = "Rôle ultra secret"
    mine = f"{ROOT}/applications/{application_id}/interviews"
    cases = [
        (mine, BODY | {"duration_min": 20}),
        (mine, BODY | {"mode": secret}),
        (mine, BODY | {"language": secret}),
        (f"{ROOT}/interviews", BODY | {"role": ""}),
        (f"{ROOT}/interviews", BODY | {"role": secret * 40}),
        (f"{ROOT}/interviews", BODY | {"posting_id": secret * 10}),
        (f"{ROOT}/interviews", BODY),
        (f"{ROOT}/interviews", BODY | {"role": "   "}),
        (f"{ROOT}/interviews", BODY | {"role": secret, "posting_id": UNKNOWN}),  # l'un ou l'autre
    ]
    for url, body in cases:
        r = await client.post(url, json=body)
        assert r.status_code == 422, (url, body)
        assert r.json()["error"]["code"] == "validation_error"
        assert secret not in r.text
        assert r.json()["error"]["details"]["fields"]
    r = await client.get(f"{ROOT}/interviews", params={"application_id": secret * 10})
    assert r.status_code == 422 and secret not in r.text


async def test_list_recent_first_and_by_application(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    launcher = spy(app)
    first_app = await ready_application(client, app)
    second_app = await ready_application(client, app, profile=False, title="Autre poste")
    user = str(app.state.local_user_id)
    ids = []
    for application_id in (first_app, second_app, first_app):
        started = await launch(client, application_id)
        ids.append(started["interview_id"])
        await save_done(app, started)
        await launcher.end(user, started["session_id"])
    everything = (await client.get(f"{ROOT}/interviews")).json()
    assert [row["id"] for row in everything] == ids[::-1]
    mine = (await client.get(f"{ROOT}/interviews", params={"application_id": first_app})).json()
    assert [row["id"] for row in mine] == [ids[2], ids[0]]
    none = await client.get(f"{ROOT}/interviews", params={"application_id": UNKNOWN})
    assert (none.status_code, none.json()["error"]["code"]) == (404, "application_not_found")


async def test_dead_session_marks_failed(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    application_id, started = await running_application(client, app)
    got = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert got["status"] == "running"
    await launcher.end(str(app.state.local_user_id), started["session_id"], "failed")
    got = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert got["status"] == "failed"
    [listed] = (await client.get(f"{ROOT}/interviews")).json()
    assert listed["status"] == "failed"
    assert (await interview_row(app, started["interview_id"])).status == "failed"
    # Un entretien en échec ne bloque plus un nouveau lancement.
    again = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY)
    assert again.status_code == 202


async def test_finished_session_without_result_marks_failed_on_list(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    launcher = spy(app)
    _, started = await running_application(client, app)
    await launcher.end(str(app.state.local_user_id), started["session_id"], "completed")
    [listed] = (await client.get(f"{ROOT}/interviews")).json()
    assert listed["status"] == "failed"


async def test_finished_interview_keeps_its_status(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    _, started = await running_application(client, app)
    await save_done(app, started)
    await launcher.end(str(app.state.local_user_id), started["session_id"])
    got = (await client.get(f"{ROOT}/interviews/{started['interview_id']}")).json()
    assert got["status"] == "done"
    assert [e["index"] for e in got["exchanges"]] == [0, 1]
    assert got["debrief"]["missed"] == [0] and got["cards_created"] == 1 and got["flags"] == []
    assert set(got["debrief"]["scores"]) == {
        "clarte",
        "structure",
        "profondeur_technique",
        "adequation",
    }
