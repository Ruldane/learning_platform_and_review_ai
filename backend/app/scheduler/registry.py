"""Tâches planifiées du back : une de plus = une ligne ici."""

from datetime import timedelta

from app.scheduler.base import JobSpec
from app.scheduler.jobs import lessons_due

JOBS: list[JobSpec] = [JobSpec("lessons_due", timedelta(minutes=15), lessons_due.run)]
