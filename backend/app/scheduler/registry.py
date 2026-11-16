"""Tâches planifiées du back : une de plus = une ligne ici."""

from datetime import timedelta

from app.scheduler.base import JobSpec
from app.scheduler.jobs import (
    ats_refresh,
    lessons_due,
    market_radar,
    reminders_due,
    skill_snapshots,
    weekly_review,
)

JOBS: list[JobSpec] = [
    JobSpec("lessons_due", timedelta(minutes=15), lessons_due.run),
    JobSpec("weekly_review", timedelta(minutes=15), weekly_review.run),
    JobSpec("skill_snapshots", timedelta(minutes=15), skill_snapshots.run),
    JobSpec("reminders_due", timedelta(hours=1), reminders_due.run),
    JobSpec("ats_refresh", timedelta(hours=6), ats_refresh.run),
    JobSpec("market_radar", timedelta(minutes=15), market_radar.run),
]
