"""Routes du comité de recrutement (D147) : lancement (202, 404, 409, 422), liste et détail, statut
qui suit la session, isolation entre utilisatrices."""

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.committee_support import (
    ROOT,
    UNKNOWN,
    add_profile,
    launch,
    ready_committee,
    run_row,
    save_done,
    spy,
    synthesis_of,
    votes_of,
)
from tests.features.applications.conftest import add_posting, add_version

pytestmark = pytest.mark.usefixtures("client")


async def test_committee_routes_202_409(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting, version = await ready_committee(client, app)
    launcher = spy(app)
    r = await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    assert r.status_code == 202, r.text
    started = r.json()
    assert set(started) == {"run_id", "session_id"}
    assert launcher.started == [("hiring_committee", {"run_id": started["run_id"]})]
    view = (await client.get(f"{ROOT}/sessions/{started['session_id']}")).json()
    assert (view["graph"], view["subject_type"], view["subject_id"]) == (
        "hiring_committee",
        "committee_run",
        started["run_id"],
    )
    got = (await client.get(f"{ROOT}/committee/{started['run_id']}")).json()
    assert (got["status"], got["votes"], got["verdict"], got["previous"]) == (
        "running",
        [],
        None,
        None,
    )
    assert got["objections"] == [] and got["changes"] == []
    assert (got["cv_version_id"], got["posting_id"]) == (version, posting)
    assert got["session_id"] == started["session_id"] and got["application_id"]
    again = await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    assert again.status_code == 409
    error = again.json()["error"]
    assert (error["code"], error["details"]) == (
        "committee_in_progress",
        {"run_id": started["run_id"]},
    )
    assert len(launcher.started) == 1
    row = await run_row(app, started["run_id"])
    assert (row.status, row.previous_id) == ("running", None)


async def test_unknown_version_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    await ready_committee(client, app)
    launcher = spy(app)
    r = await client.post(f"{ROOT}/committee", json={"cv_version_id": UNKNOWN})
    assert (r.status_code, r.json()["error"]["code"]) == (404, "version_not_found")
    assert launcher.started == []


async def test_version_not_ready_409(client: httpx.AsyncClient, app: FastAPI) -> None:
    await add_profile(app)
    launcher = spy(app)
    version = await add_version(app, await add_posting(app), status="rendering")
    r = await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "version_not_ready")
    assert launcher.started == []


async def test_profile_required_409(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, version = await ready_committee(client, app, profile=False)
    r = await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "profile_required")
    assert spy(app).started == []


async def test_422_no_echo(client: httpx.AsyncClient, app: FastAPI) -> None:
    secret = "valeur-ultra-secrète-" + "x" * 40
    for body in ({}, {"cv_version_id": ""}, {"cv_version_id": secret}, {"cv_version_id": 3}):
        r = await client.post(f"{ROOT}/committee", json=body | {"extra": secret})
        assert r.status_code in (404, 422), r.text
        assert secret not in r.text
    r = await client.post(f"{ROOT}/committee", json={})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["cv_version_id"]
    assert (await client.get(f"{ROOT}/committee", params={"posting_id": ""})).status_code == 422


async def test_refused_launch_marks_failed(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting, version = await ready_committee(client, app)
    launcher = spy(app)
    launcher.refuse = True
    r = await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    assert (r.status_code, r.json()["error"]["code"]) == (503, "engine_unavailable")
    [row] = (await client.get(f"{ROOT}/committee", params={"posting_id": posting})).json()
    assert row["status"] == "failed"
    launcher.refuse = False
    assert (
        await client.post(f"{ROOT}/committee", json={"cv_version_id": version})
    ).status_code == 202


async def test_dead_session_marks_failed(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting, version = await ready_committee(client, app)
    started = await launch(client, version)
    launcher = spy(app)
    await launcher.end(str(app.state.local_user_id), started["session_id"], "failed")
    got = (await client.get(f"{ROOT}/committee/{started['run_id']}")).json()
    assert got["status"] == "failed" and got["verdict"] is None
    assert (await run_row(app, started["run_id"])).status == "failed"
    # Une exécution en échec ne bloque plus un nouveau lancement.
    await launch(client, version)
    done = await client.get(f"{ROOT}/committee", params={"posting_id": posting})
    assert [row["status"] for row in done.json()] == ["running", "failed"]


async def test_finished_session_without_result_marks_failed(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    _, version = await ready_committee(client, app)
    started = await launch(client, version)
    await spy(app).end(str(app.state.local_user_id), started["session_id"], "completed")
    [listed] = (await client.get(f"{ROOT}/committee")).json()
    assert listed["status"] == "failed"


async def test_done_run_keeps_its_status_and_result(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    _, version = await ready_committee(client, app)
    started = await launch(client, version)
    await save_done(
        app, started, votes_of("oui", "oui", "non", "peut_etre"), synthesis_of("peut_etre")
    )
    await spy(app).end(str(app.state.local_user_id), started["session_id"])
    got = (await client.get(f"{ROOT}/committee/{started['run_id']}")).json()
    assert (got["status"], got["verdict"]) == ("done", "peut_etre")
    assert [(v["persona"], v["vote"]) for v in got["votes"]] == [
        ("ats_reader", "oui"),
        ("recruiter", "oui"),
        ("manager", "non"),
        ("colleague", "peut_etre"),
    ]
    assert got["votes"][0]["objection"] and got["votes"][0]["reason"]
    assert [o["text"] for o in got["objections"]][0] == "Aucun mot clé LangGraph dans le CV"
    assert len(got["changes"]) == 3 and got["previous"] is None
    assert set(got["changes"][2]) == {"text", "persona", "fact_ids", "needs_skill", "terms"}


async def test_list_filters_by_posting_most_recent_first(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    posting, version = await ready_committee(client, app)
    first = await launch(client, version)
    await spy(app).end(str(app.state.local_user_id), first["session_id"], "failed")
    second = await launch(client, version)
    other = await add_version(app, await add_posting(app))
    third = await launch(client, other)
    mine = (await client.get(f"{ROOT}/committee", params={"posting_id": posting})).json()
    assert [row["id"] for row in mine] == [second["run_id"], first["run_id"]]
    everything = (await client.get(f"{ROOT}/committee")).json()
    assert [row["id"] for row in everything] == [third["run_id"], second["run_id"], first["run_id"]]
