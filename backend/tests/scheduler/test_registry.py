"""Le registre des tâches planifiées : une de plus = une ligne (D91). Les noms attendus sont
complétés par les tâches suivantes de la phase 8 (brief, radar, projets)."""

from datetime import timedelta

from app.scheduler.registry import JOBS

EXPECTED = {
    "lessons_due",
    "weekly_review",
    "skill_snapshots",
    "reminders_due",
    "ats_refresh",
    "market_radar",
    "daily_brief",
}


def test_registry_lists_every_scheduled_job() -> None:
    names = [spec.name for spec in JOBS]
    assert set(names) >= EXPECTED
    assert len(names) == len(set(names))  # un nom de tâche, une ligne
    assert all(spec.every > timedelta(0) for spec in JOBS)
    ats = next(spec for spec in JOBS if spec.name == "ats_refresh")
    assert ats.every == timedelta(hours=6) and ats.at_startup
