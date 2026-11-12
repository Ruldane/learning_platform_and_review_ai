"""Statut d'une leçon tel qu'il est montré (D91).

Une session `lesson_factory` qui s'arrête hors du port (Vérificateur invalide, quota, annulation)
laisse sa leçon `generating`. La base n'est corrigée que sous le verrou des leçons du programme
(`ensure_lessons`, au plus tard au passage suivant de la tâche planifiée) ; d'ici là, chaque
lecture montre déjà la leçon en échec, sans rien écrire. Une leçon `generating` sans session
encore rangée est en cours de lancement : elle reste `generating`."""

import builtins

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sessions.service import list_open_sessions

GRAPH = "lesson_factory"
SUBJECT = "program"
INTERRUPTED = "La production de la leçon s'est arrêtée avant la fin : elle sera relancée."


async def open_lesson_sessions(
    db: AsyncSession, user_id: str, program_id: str
) -> builtins.list[str]:
    """Sessions de leçon ouvertes du programme (une au plus en temps normal)."""
    return await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=program_id
    )


def interrupted(status: str, session_id: str | None, open_ids: builtins.list[str]) -> bool:
    """Leçon `generating` dont la session rangée n'est plus ouverte (terminée, échouée,
    annulée)."""
    return status == "generating" and session_id is not None and session_id not in open_ids


def shown(
    status: str, session_id: str | None, reason: str | None, open_ids: builtins.list[str]
) -> tuple[str, str | None]:
    """`(statut, raison)` à montrer : une leçon interrompue apparaît en échec."""
    if interrupted(status, session_id, open_ids):
        return "failed", INTERRUPTED
    return status, reason
