"""Relevé hebdomadaire et premier lancement (D197) : un compte dont le premier lancement n'est pas
fini ne prend ni passage ni recherche web."""

from datetime import timedelta

from app.features.radar.service.schedule import run_weekly_radar
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.radar.support import ROLE, Radar, add_users
from tests.features.radar.test_schedule import MONDAY_9H, _jobs, _runs, _settings
from tests.support.onboarding import finish_first_launch


async def test_weekly_waits_for_the_first_launch(radar: Radar, launcher: RecordingLauncher) -> None:
    """D197 : un compte au premier lancement non fini ne prend ni passage ni recherche web ; il est
    traité au premier passage qui suit."""
    await add_users(radar.factory, "neuf", onboarded=False)
    await _settings(radar, "neuf", radar_role=ROLE, radar_zone="Lyon")
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 0  # ME et OTHER n'ont pas de poste
    assert await _jobs(radar, "neuf") == [] and await _runs(radar, "neuf") == []
    assert launcher.started == []
    await finish_first_launch(radar.factory, "neuf")
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(minutes=15)) == 1
    assert [job.status for job in await _jobs(radar, "neuf")] == ["done"]
