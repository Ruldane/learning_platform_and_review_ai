"""Tâche « rafraîchissement ATS » (P14, D158) : toutes les 6 heures et au démarrage, chaque compte
dont le dernier rafraîchissement date de 30 jours ou plus reçoit une session `web_research` sur le
fonctionnement des ATS. Le travail est dans la feature `cv` (`run_ats_refresh`), qui n'importe
jamais ce paquet (contrat 8) : la tâche ne fait que déballer son contexte et lire l'heure."""

from datetime import UTC, datetime

from app.features.cv.service.ats_refresh import run_ats_refresh
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_ats_refresh(ctx.session_factory, ctx.launcher, datetime.now(UTC))
