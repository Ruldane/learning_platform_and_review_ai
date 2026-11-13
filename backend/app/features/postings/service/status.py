"""Statut d'une offre et de son écart tels qu'ils sont montrés (D122, même motif que D91 et D101).

Une session `gap_analysis` qui s'arrête hors du port (sortie illisible, délai, annulation, arrêt
du serveur) laisse son offre `analyzing`, ou `ready` sans écart. Chaque lecture la montre déjà en
échec, avec `gap_session_id`, sans écrire ; la base n'est corrigée qu'à la relance (nouvel envoi
du même lien ou du même texte, `POST /postings/{id}/gap`), sous le verrou de l'offre.

Ordre des lectures (D97 n° 9) : sessions ouvertes, PUIS lignes ; si une ligne paraît
interrompue, les sessions sont relues (celle lancée entre les deux lectures compte ouverte)."""

from collections.abc import Awaitable, Callable, Iterable
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.postings import JobPosting
from app.features.postings.service.runtime import GRAPH, SUBJECT
from app.features.sessions.service import list_open_sessions, list_open_sessions_by_subject

INTERRUPTED = "L'analyse de l'offre s'est arrêtée avant la fin : relance-la."
LAUNCH_FAILED = "L'analyse de l'offre n'a pas pu démarrer : relance-la."
GapStatus = Literal["pending", "ready", "failed"]


async def open_sessions(db: AsyncSession, user_id: str, posting_id: str) -> list[str]:
    return await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=posting_id
    )


async def open_sessions_by_posting(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    return await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)


def running(posting: JobPosting, open_ids: Iterable[str]) -> bool:
    """La session rangée de l'offre tourne encore."""
    return posting.gap_session_id is not None and posting.gap_session_id in set(open_ids)


def interrupted(posting: JobPosting, open_ids: Iterable[str]) -> bool:
    """Offre en analyse dont la session n'est plus ouverte (ou jamais rangée)."""
    return posting.status == "analyzing" and not running(posting, open_ids)


def shown_status(posting: JobPosting, open_ids: Iterable[str]) -> tuple[str, str | None]:
    """`(statut, raison)` de l'offre à montrer."""
    if interrupted(posting, open_ids):
        return "failed", INTERRUPTED
    return posting.status, posting.failure_reason


def gap_status(posting: JobPosting, open_ids: Iterable[str]) -> GapStatus:
    """`ready` : l'écart de la session rangée est écrit (ou un plus ancien, si plus rien ne
    tourne) ; `pending` : la session tourne ; sinon `failed` (offre refusée comprise)."""
    gap = posting.gap
    if posting.status == "rejected":
        return "failed"
    if gap is not None and gap.get("session_id") == posting.gap_session_id:
        return "ready"
    if running(posting, open_ids):
        return "pending"
    return "ready" if gap is not None else "failed"


def needs_launch(posting: JobPosting, open_ids: Iterable[str]) -> bool:
    """Une offre déjà ajoutée est relancée plutôt que rendue telle quelle si elle est refusée, en
    échec, interrompue, ou analysée sans écart alors que plus rien ne tourne."""
    if posting.status in ("rejected", "failed"):
        return True
    return not running(posting, open_ids) and posting.gap is None


async def read_with_sessions[R](
    db: AsyncSession,
    user_id: str,
    read: Callable[[], Awaitable[R]],
    postings: Callable[[R], Iterable[JobPosting]],
) -> tuple[R, dict[str, list[str]]]:
    """`(lignes lues par read, sessions ouvertes par offre)` dans l'ordre sûr."""
    open_ids = await open_sessions_by_posting(db, user_id)
    rows = await read()
    if any(needs_launch(p, open_ids.get(p.id, [])) for p in postings(rows)):
        later = await open_sessions_by_posting(db, user_id)
        for key, ids in later.items():
            open_ids[key] = list(dict.fromkeys([*open_ids.get(key, []), *ids]))
    return rows, open_ids
