"""Lancer un relevé (P10, D160) : 202 puis 409, poste obligatoire, poste et zone mémorisés, session
`market_radar` sujet `radar_run`, relevé dont la session est morte corrigé à la lecture (code
lisible), lancement refusé, 422 sans écho, relevés d'une autre utilisatrice invisibles."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.agents import AgentSession
from app.db.models.daily import RadarRun
from app.features.settings.service import SettingsService
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.radar.support import OTHER, ROLE, ZONE, add_users
from tests.features.skills.support import add_goal

API = "/api/v1/radar"


async def _runs(app: FastAPI) -> list[RadarRun]:
    async with app.state.session_factory() as db:
        return list((await db.execute(select(RadarRun).order_by(RadarRun.created_at))).scalars())


async def _settings(app: FastAPI):  # type: ignore[no-untyped-def]
    async with app.state.session_factory() as db:
        return await SettingsService(db, app.state.local_user_id).get()


async def _start(client: httpx.AsyncClient, **body: object) -> httpx.Response:
    return await client.post(f"{API}/runs", json=body)


async def test_start_run_202_then_409(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    started = await _start(client, role=ROLE, zone=ZONE)
    assert started.status_code == 202, started.text
    run_id, session_id = started.json()["run_id"], started.json()["session_id"]
    assert launcher_spy.started == [("market_radar", {"run_id": run_id})]
    async with app.state.session_factory() as db:
        session = (await db.execute(select(AgentSession))).scalar_one()
    assert (session.id, session.graph, session.subject_type, session.subject_id) == (
        session_id,
        "market_radar",
        "radar_run",
        run_id,
    )
    [row] = await _runs(app)
    assert (row.status, row.trigger, row.session_id, row.period) == (
        "running",
        "manual",
        session_id,
        None,
    )
    again = await _start(client, role=ROLE)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "radar_in_progress"
    assert again.json()["error"]["details"] == {"run_id": run_id}
    assert len(launcher_spy.started) == 1 and len(await _runs(app)) == 1


async def test_role_required_without_goal_or_setting(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    refused = await client.post(f"{API}/runs")  # sans corps
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "radar_role_required"
    assert launcher_spy.started == [] and await _runs(app) == []
    latest = (await client.get(f"{API}/latest")).json()
    assert latest["defaults"] == {"role": "", "zone": "France"}


async def test_default_role_comes_from_the_settings_then_the_latest_goal(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    await add_goal(app.state.session_factory, app.state.local_user_id, target_role="Data engineer")
    assert (await client.get(f"{API}/latest")).json()["defaults"]["role"] == "Data engineer"
    started = await client.post(f"{API}/runs")
    assert started.status_code == 202
    [row] = await _runs(app)
    assert (row.role, row.zone) == ("Data engineer", "France")
    assert (await _settings(app)).radar_role == ""  # rien donné : rien de mémorisé


async def test_role_and_zone_saved_in_settings(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    assert (await _start(client, role="  Ingénieur IA  ", zone="Lyon")).status_code == 202
    settings = await _settings(app)
    assert (settings.radar_role, settings.radar_zone) == (ROLE, ZONE)
    [row] = await _runs(app)
    assert (row.role, row.zone, row.role_norm, row.zone_norm) == (
        ROLE,
        ZONE,
        "ingenieur ia",
        "lyon",
    )
    await _end(app, row)
    # Le prochain relevé, sans rien donner, reprend les réglages.
    assert (await client.get(f"{API}/latest")).json()["defaults"] == {"role": ROLE, "zone": ZONE}
    assert (await client.post(f"{API}/runs")).status_code == 202
    # Une zone seule garde le poste des réglages.
    runs = await _runs(app)
    await _end(app, runs[-1])
    assert (await _start(client, zone="Paris")).status_code == 202
    assert (await _runs(app))[-1].role == ROLE
    assert (await _settings(app)).radar_zone == "Paris"


async def _end(app: FastAPI, row: RadarRun, status: str = "completed") -> None:
    async with app.state.session_factory() as db:
        session = (
            await db.execute(select(AgentSession).where(AgentSession.id == row.session_id))
        ).scalar_one()
        session.status = status
        await db.commit()


async def test_dead_session_marks_run_failed(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    """Le statut suit la session : un relevé dont la session est `failed` (délai d'un nœud,
    panne de l'Analyste…) devient `failed`, avec un code, dès la lecture suivante ; un nouveau
    relevé n'est alors plus refusé."""
    first = (await _start(client, role=ROLE)).json()["run_id"]
    [row] = await _runs(app)
    await _end(app, row, "failed")
    latest = (await client.get(f"{API}/latest")).json()
    assert latest["running"] is None
    assert latest["latest"]["id"] == first
    assert (latest["latest"]["status"], latest["latest"]["error_code"]) == (
        "failed",
        "session_failed",
    )
    assert latest["latest"]["finished_at"] is not None
    second = await _start(client)
    assert second.status_code == 202 and second.json()["run_id"] != first


@pytest.mark.parametrize(
    ("status", "code"),
    [
        ("failed", "session_failed"),
        ("cancelled", "session_cancelled"),
        ("completed", "not_finalized"),
    ],
)
async def test_each_dead_session_gets_a_readable_code(
    client: httpx.AsyncClient,
    launcher_spy: RecordingLauncher,
    app: FastAPI,
    status: str,
    code: str,
) -> None:
    await _start(client, role=ROLE)
    await _end(app, (await _runs(app))[0], status)
    listed = (await client.get(f"{API}/runs")).json()
    assert [(r["status"], r["error_code"]) for r in listed] == [("failed", code)]


async def test_running_session_keeps_the_run_running(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    run_id = (await _start(client, role=ROLE)).json()["run_id"]
    for _ in range(2):  # lire ne tue pas un relevé vivant
        latest = (await client.get(f"{API}/latest")).json()
        assert latest["running"]["id"] == run_id and latest["latest"] is None
    assert (await client.get(f"{API}/runs/{run_id}")).json()["status"] == "running"


async def test_run_without_a_session_is_failed_on_read(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """Un relevé laissé sans session (arrêt entre sa création et son lancement) ne bloque rien."""
    async with app.state.session_factory() as db:
        db.add(
            RadarRun(
                user_id=app.state.local_user_id,
                role=ROLE,
                zone=ZONE,
                role_norm="r",
                zone_norm="z",
                trigger="manual",
            )
        )
        await db.commit()
    [item] = (await client.get(f"{API}/runs")).json()
    assert (item["status"], item["error_code"]) == ("failed", "launch_failed")


async def test_refused_launch_marks_the_run_failed(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    launcher_spy.refuse = True
    refused = await _start(client, role=ROLE)
    assert refused.status_code == 503 and refused.json()["error"]["code"] == "engine_unavailable"
    [row] = await _runs(app)
    assert (row.status, row.error_code, row.session_id) == ("failed", "engine_unavailable", None)
    launcher_spy.refuse = False
    assert (await _start(client)).status_code == 202  # le poste donné plus haut est mémorisé


@pytest.mark.parametrize("body", [{"role": "x"}, {"role": "x" * 121}, {"zone": ""}, {"role": 12}])
async def test_422_never_echoes_role(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, body: dict[str, object]
) -> None:
    response = await client.post(f"{API}/runs", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {"fields": [next(iter(body))]}
    assert "x" * 5 not in response.text and "12" not in response.text
    assert launcher_spy.started == []


async def test_other_user_run_404(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    await add_users(app.state.session_factory, OTHER)
    async with app.state.session_factory() as db:
        row = RadarRun(
            user_id=OTHER,
            role=ROLE,
            zone=ZONE,
            role_norm="r",
            zone_norm="z",
            trigger="manual",
            status="done",
        )
        db.add(row)
        await db.commit()
        other_id = row.id
    missing = await client.get(f"{API}/runs/{other_id}")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "radar_run_not_found"
    assert (await client.get(f"{API}/runs")).json() == []
    assert (await client.get(f"{API}/latest")).json()["latest"] is None
    # Le relevé d'une autre ne bloque pas non plus un lancement.
    assert (await _start(client, role=ROLE)).status_code == 202
