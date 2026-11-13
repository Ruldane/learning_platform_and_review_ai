"""Tâche « bilan hebdomadaire » (SPEC F13, 11.4 ; D106) : toutes les 15 minutes et au démarrage,
chaque programme validé dont l'heure du bilan est passée chez January reçoit son bilan de la
semaine (une fois) et une proposition de replanification. Le travail est dans la feature
`replan` (`run_weekly_reviews`), qui n'importe jamais ce paquet (contrat 8) : la tâche ne fait
que déballer son contexte et lire l'heure."""

from datetime import UTC, datetime

from app.features.replan.service.weekly import run_weekly_reviews
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_weekly_reviews(ctx.session_factory, ctx.replan, datetime.now(UTC))
