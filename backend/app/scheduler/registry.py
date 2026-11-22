"""Tâches planifiées du back : une de plus = une ligne ici."""

from datetime import timedelta

from app.scheduler.base import JobSpec
from app.scheduler.jobs import (
    ats_refresh,
    daily_brief,
    lessons_due,
    market_radar,
    mcp_housekeeping,
    project_briefs,
    reading_stack,
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
    JobSpec("daily_brief", timedelta(minutes=10), daily_brief.run),
    JobSpec("reading_stack", timedelta(minutes=15), reading_stack.run),
    JobSpec("project_briefs", timedelta(minutes=15), project_briefs.run),
    JobSpec("mcp_housekeeping", timedelta(minutes=10), mcp_housekeeping.run),
]
