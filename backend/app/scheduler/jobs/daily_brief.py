"""Tâche « brief du matin » (P12, D162) : toutes les 10 minutes et au démarrage, chaque compte dont
l'heure du brief est passée reçoit le brief de son jour local (une seule fois, même s'il a déjà
été créé à l'ouverture de l'accueil). Le travail est dans la feature `brief`
(`run_daily_briefs`), qui n'importe jamais ce paquet (contrat 8) : la tâche ne fait que déballer
son contexte et lire l'heure."""

from datetime import UTC, datetime

from app.features.brief.service.schedule import run_daily_briefs
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_daily_briefs(ctx.daily.brief, datetime.now(UTC))
