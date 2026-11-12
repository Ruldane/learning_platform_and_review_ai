"""Tâche « J-7 » (SPEC 3.5, D91) : toutes les 6 h et au démarrage, chaque programme validé voit
sa chaîne de leçons relancée si besoin (`ensure_lessons` : semaine qui commence dans 7 jours au
plus, leçon interrompue en échec, nouvel essai d'une leçon en échec). Sans table `jobs` (phase 8) :
l'état des leçons suffit à l'idempotence. Une panne sur un programme n'arrête pas les autres.
Journaux : identifiants et type d'erreur seulement."""

import logging

from app.features.lessons.service.production import ensure_lessons, list_programs_due
from app.scheduler.base import JobContext

logger = logging.getLogger(__name__)


async def run(ctx: JobContext) -> None:
    programs = await list_programs_due(ctx.session_factory)
    launched = 0
    for user_id, program_id in programs:
        try:
            launched += await ensure_lessons(ctx.production, user_id, program_id) is not None
        except Exception as exc:
            logger.warning(
                "Leçons J-7 : programme %s non traité (%s)", program_id, type(exc).__name__
            )
    logger.info("Leçons J-7 : %d programme(s), %d leçon(s) lancée(s)", len(programs), launched)
