"""Lancement de l'analyse d'une offre (parcours `gap_analysis`, D121, D122), sous le verrou de
l'offre : une seule session à la fois. `gap_session_id` est posé dès que la session existe ; un
lancement qui échoue passe l'offre en `failed` (raison fixe) avant de relever l'erreur. Une offre
refusée, en échec, interrompue ou sans écart est relancée : statut remis à `analyzing` (ou
`ready` si son analyse est rangée), raison effacée. Journaux : identifiants seulement."""

import logging

from app.core.errors import AppError
from app.features.postings.repository import PostingRepository
from app.features.postings.service.duplicates import not_found
from app.features.postings.service.runtime import GRAPH, SUBJECT, PostingsRuntime
from app.features.postings.service.status import (
    LAUNCH_FAILED,
    needs_launch,
    open_sessions,
    running,
)

logger = logging.getLogger(__name__)


def gap_in_progress() -> AppError:
    return AppError("gap_in_progress", "L'analyse de cette offre est déjà en cours.", 409)


async def _set_session(rt: PostingsRuntime, user_id: str, posting_id: str, sid: str | None) -> None:
    async with rt.session_factory() as db:
        posting = await PostingRepository(db, user_id).get_fresh(posting_id)
        if posting is None:
            return
        if sid is not None:
            posting.gap_session_id = sid
        else:
            posting.status, posting.failure_reason = "failed", LAUNCH_FAILED
        await db.commit()


async def _start(rt: PostingsRuntime, user_id: str, posting_id: str) -> str:
    """À appeler sous le verrou de l'offre."""
    try:
        sid = await rt.launcher.start(
            user_id, GRAPH, {"posting_id": posting_id}, subject_type=SUBJECT, subject_id=posting_id
        )
    except BaseException:
        await _set_session(rt, user_id, posting_id, None)
        logger.warning("Analyse d'offre non lancée : utilisateur %s, offre %s", user_id, posting_id)
        raise
    await _set_session(rt, user_id, posting_id, sid)
    logger.info(
        "Analyse d'offre lancée : utilisateur %s, offre %s, session %s", user_id, posting_id, sid
    )
    return sid


async def launch_new(rt: PostingsRuntime, user_id: str, posting_id: str) -> str:
    """L'analyse d'une offre qui vient d'être ajoutée."""
    async with rt.launch_locks.get(user_id, posting_id):
        return await _start(rt, user_id, posting_id)


async def relaunch(
    rt: PostingsRuntime, user_id: str, posting_id: str, *, if_needed: bool
) -> str | None:
    """Relance l'analyse. `if_needed` (offre de nouveau envoyée) : seulement si `needs_launch`,
    sinon `None`. Sans lui (`POST /postings/{id}/gap`) : toujours, sauf session en cours
    (409 `gap_in_progress`). Offre absente ou d'une autre : 404."""
    async with rt.launch_locks.get(user_id, posting_id):
        async with rt.session_factory() as db:
            open_ids = await open_sessions(db, user_id, posting_id)
            posting = await PostingRepository(db, user_id).get_fresh(posting_id)
            if posting is None:
                raise not_found()
            if running(posting, open_ids):
                if if_needed:
                    return None
                raise gap_in_progress()
            if if_needed and not needs_launch(posting, open_ids):
                return None
            posting.status = "analyzing" if posting.analysis is None else "ready"
            posting.failure_reason, posting.gap_session_id = None, None
            await db.commit()
        return await _start(rt, user_id, posting_id)
