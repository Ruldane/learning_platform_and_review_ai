"""Journaux du radar (17.2) : identifiants, nombres et codes seulement. Jamais le poste, la zone,
un lien, un site, un intitulé, une entreprise, un texte d'offre ni une compétence."""

import logging
from datetime import timedelta

import httpx
import pytest

from app.features.radar.service.schedule import run_weekly_radar
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.radar.support import ME, ROLE, ZONE, Radar, link

SECRETS = (
    ROLE,
    ZONE,
    "example.org",
    "ferme",
    "linkedin",
    "Société",
    "Poste p",
    "Offre fictive",
    "Python",
    "Camille",
)


def _text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


async def test_radar_data_never_logged(
    caplog: pytest.LogCaptureFixture, radar: Radar, launcher: RecordingLauncher
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    run_id = await radar.new_run()
    await radar.store.context(ME, run_id)
    await radar.store.save_candidates(ME, "s", run_id, 6, [link(1)])
    await radar.read(run_id, 4)
    await radar.store.read_posting(ME, "s", run_id, link(9, "ferme.example.org"))
    await radar.store.read_posting(ME, "s", run_id, "https://www.linkedin.com/jobs/view/1")
    await radar.store.read_posting(ME, "s", run_id, "ftp://refuse.example.org/x")
    await radar.extract(run_id, [["Python"]] * 4)
    await radar.store.finalize(ME, "s", run_id)
    failed = await radar.new_run(role="Autre poste secret")
    await radar.store.fail(ME, "s", failed, "search_unavailable")
    assert "Autre poste secret" not in _text(caplog)
    text = _text(caplog)
    for secret in SECRETS:
        assert secret not in text, secret
    assert run_id in text  # des identifiants et des nombres, oui


async def test_weekly_and_start_run_never_log_the_role(
    caplog: pytest.LogCaptureFixture, radar: Radar, launcher: RecordingLauncher
) -> None:
    from tests.features.radar.test_schedule import MONDAY_9H, _settings

    caplog.set_level(logging.DEBUG, logger="app")
    await _settings(radar, radar_role=ROLE, radar_zone=ZONE)
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    await _settings(radar, ME, radar_role="Poste secret")
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=7)) == 0  # le premier vit
    text = _text(caplog)
    for secret in (ROLE, ZONE, "Poste secret"):
        assert secret not in text
    assert "run" in text.casefold()


async def test_routes_never_log_the_role_zone_or_422_input(
    caplog: pytest.LogCaptureFixture,
    client: httpx.AsyncClient,
    launcher_spy: RecordingLauncher,
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await client.post("/api/v1/radar/runs", json={"role": ROLE, "zone": ZONE})
    await client.post("/api/v1/radar/runs", json={"role": "Poste secret", "zone": "Zone secrète"})
    await client.post("/api/v1/radar/runs", json={"role": "x", "zone": "Zone secrète"})
    await client.get("/api/v1/radar/latest")
    text = _text(caplog)
    for secret in (ROLE, ZONE, "Poste secret", "Zone secrète"):
        assert secret not in text, secret
