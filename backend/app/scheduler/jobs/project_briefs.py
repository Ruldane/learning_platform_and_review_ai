"""Tâche « énoncés des mini projets » (P1, D166) : toutes les 15 minutes et au démarrage, chaque
module non sauté d'un programme validé dont la semaine a commencé reçoit son projet et l'énoncé
du Praticien. Le travail est dans la feature `projects` (`ensure_project_briefs`), qui n'importe
jamais ce paquet (contrat 8) : la tâche ne fait que déballer son contexte et lire l'heure. Au
démarrage, ce même passage corrige les projets dont la session est morte (statut qui suit la
session)."""

from datetime import UTC, datetime

from app.features.projects.service.briefs import ensure_project_briefs
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await ensure_project_briefs(ctx.daily.projects, datetime.now(UTC))
