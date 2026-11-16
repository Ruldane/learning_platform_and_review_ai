"""Tâche « relevé hebdomadaire du radar » (P10, D160) : toutes les 15 minutes et au démarrage, le
lundi à partir de 06:00 locales, chaque compte reçoit un relevé du marché, une fois par semaine ISO
locale. Le travail est dans la feature `radar` (`run_weekly_radar`), qui n'importe jamais ce
paquet (contrat 8) : la tâche ne fait que déballer son contexte et lire l'heure."""

from datetime import UTC, datetime

from app.features.radar.service.schedule import run_weekly_radar
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_weekly_radar(ctx.daily.radar, datetime.now(UTC))
