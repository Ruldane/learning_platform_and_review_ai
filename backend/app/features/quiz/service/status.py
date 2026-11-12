"""Statut d'un quiz ou d'une tentative tel qu'il est montré (D101, même motif que D91).

Une session `quiz` qui s'arrête hors du port (sortie illisible trois fois, délai, annulation)
laisse son quiz `generating` ou sa tentative `grading`. Chaque lecture les montre déjà en échec,
sans écrire ; la base n'est corrigée que sous le verrou du quiz (relance, nouvelle tentative).
Une ligne sans session encore rangée est en cours de lancement : elle reste telle quelle.

Ordre des lectures (D97 n° 9) : sessions ouvertes, PUIS lignes. Si une ligne paraît
interrompue, les sessions sont relues : celle lancée entre les deux lectures compte ouverte."""

from collections.abc import Awaitable, Callable, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.quiz.service.runtime import GRAPH, SUBJECT
from app.features.sessions.service import list_open_sessions

QUIZ_INTERRUPTED = "La préparation du quiz s'est arrêtée avant la fin : relance-la."
LIVE = {"generating", "grading"}


async def open_sessions(db: AsyncSession, user_id: str, quiz_id: str) -> list[str]:
    """Sessions `quiz` ouvertes sur ce quiz (écriture du quiz ou notation d'une tentative)."""
    return await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=quiz_id
    )


def interrupted(status: str, session_id: str | None, open_ids: list[str]) -> bool:
    """Quiz `generating` ou tentative `grading` dont la session rangée n'est plus ouverte
    (terminée sans le port, échouée, annulée)."""
    return status in LIVE and session_id is not None and session_id not in open_ids


async def read_with_sessions[R](
    db: AsyncSession,
    user_id: str,
    quiz_id: str,
    read: Callable[[], Awaitable[R]],
    states: Callable[[R], Iterable[tuple[str, str | None]]],
) -> tuple[R, list[str]]:
    """`(lignes lues par read, sessions ouvertes du quiz)` dans l'ordre sûr."""
    open_ids = await open_sessions(db, user_id, quiz_id)
    rows = await read()
    if any(interrupted(st, sid, open_ids) for st, sid in states(rows)):
        later = await open_sessions(db, user_id, quiz_id)
        open_ids += [sid for sid in later if sid not in open_ids]
    return rows, open_ids


def quiz_shown(
    status: str, session_id: str | None, reason: str | None, open_ids: list[str]
) -> tuple[str, str | None]:
    """`(statut, raison)` du quiz à montrer."""
    if interrupted(status, session_id, open_ids):
        return "failed", QUIZ_INTERRUPTED
    return status, reason


def attempt_shown(status: str, session_id: str | None, open_ids: list[str]) -> str:
    return "failed" if interrupted(status, session_id, open_ids) else status
