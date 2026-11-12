"""Statut d'une leçon tel qu'il est montré (D91).

Une session `lesson_factory` qui s'arrête hors du port (Vérificateur invalide, quota, annulation)
laisse sa leçon `generating`. La base n'est corrigée que sous le verrou des leçons du programme
(`ensure_lessons`, au plus tard au passage suivant de la tâche planifiée) ; d'ici là, chaque
lecture montre déjà la leçon en échec, sans rien écrire. Une leçon `generating` sans session
encore rangée est en cours de lancement : elle reste `generating`.

Ordre des lectures (`read_with_open_sessions`, D97) : sessions ouvertes, PUIS lignes de leçon.
Une leçon finie entre les deux est lue prête (la publication précède la fin de sa session) :
jamais montrée en échec. Si une leçon paraît interrompue, les sessions sont relues après les
lignes : celle d'une leçon lancée entre les deux lectures compte alors comme ouverte."""

import builtins
from collections.abc import Awaitable, Callable, Iterable

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


async def read_with_open_sessions[R](
    db: AsyncSession,
    user_id: str,
    program_id: str,
    read: Callable[[], Awaitable[R]],
    states: Callable[[R], Iterable[tuple[str, str | None]]],
) -> tuple[R, builtins.list[str]]:
    """`(lignes lues par read, sessions ouvertes)` dans l'ordre sûr ; `states` donne
    `(statut, session)` de chaque leçon lue."""
    open_ids = await open_lesson_sessions(db, user_id, program_id)
    rows = await read()
    if any(interrupted(st, sid, open_ids) for st, sid in states(rows)):
        later = await open_lesson_sessions(db, user_id, program_id)
        open_ids += [sid for sid in later if sid not in open_ids]
    return rows, open_ids


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
