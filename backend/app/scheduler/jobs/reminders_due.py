"""Tâche « relances » (SPEC 6.2, D140) : toutes les heures et au démarrage, adopte les versions de
CV de chaque compte puis synchronise ses relances attendues. Le travail est dans la feature
`applications` (`run_reminders`), qui n'importe jamais ce paquet (contrat 8) : la tâche ne fait que
déballer son contexte et lire l'heure."""

from app.features.applications.service.reminders import run_reminders
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_reminders(ctx.applications, ctx.applications.now())
