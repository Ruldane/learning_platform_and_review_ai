"""Tâche « relevés des compétences » (SPEC F15, D106) : toutes les 15 minutes et au démarrage,
un relevé des niveaux par utilisateur et par semaine locale (le premier passage de la semaine
l'écrit, `INSERT … ON CONFLICT DO NOTHING`). La courbe de progression (5.10) les lit."""

from datetime import UTC, datetime

from app.features.skills.service import write_weekly_snapshots
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await write_weekly_snapshots(ctx.session_factory, datetime.now(UTC))
