"""Les entretiens blancs côté API (SPEC F10, D146) : lancement du parcours `interview` depuis une
fiche ou librement (offre ou intitulé seul), liste et détail.

- Un seul entretien ouvert par utilisatrice (409 `interview_in_progress`, `details.interview_id`),
  sous le verrou des entretiens ; l'entretien est rangé (`running`) AVANT le lancement : le parcours
  le relit dans sa propre session. Un lancement refusé par le moteur le passe en `failed`.
- Le statut suit l'issue de la session (comme D129 n° 5) : un entretien `running` dont la session
  n'est plus ouverte (panne, délai, annulation) passe en `failed` à la lecture suivante, sous le
  verrou ; une session terminée ne reprend jamais, la correction est sûre. `done`, `stopped` et
  `debrief_failed` sont posés par le port (`interview_store`) et ne changent plus.

Journaux : identifiants et statuts seulement, jamais l'intitulé, une question ni une réponse."""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.applications import Interview
from app.features.applications.repository import ApplicationRepository
from app.features.applications.repository_interviews import InterviewRepository
from app.features.applications.schemas_interviews import (
    DebriefOut,
    ExchangeOut,
    FreeInterviewIn,
    InterviewIn,
    InterviewOut,
    InterviewStartOut,
)
from app.features.applications.service.interview_context import DEFAULT_ROLE
from app.features.applications.service.kit_store import profile_required
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application, invalid, not_found
from app.features.cv.service.versions import validated_profile
from app.features.postings.service.queries import get_posting
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

GRAPH = "interview"
SUBJECT = "interview"


def interview_not_found() -> AppError:
    return AppError("interview_not_found", "Entretien introuvable.", 404)


def interview_in_progress(interview_id: str) -> AppError:
    return AppError(
        "interview_in_progress",
        "Un entretien blanc est déjà en cours : termine-le ou arrête-le d'abord.",
        409,
        {"interview_id": interview_id},
    )


def interview_lock(rt: ApplicationsRuntime, user_id: str) -> asyncio.Lock:
    """Un verrou par utilisatrice : lancement, résultat rangé et lecture ne se croisent pas."""
    return rt.locks.get(user_id, "interviews")


async def interview_row(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
    """L'entretien de l'utilisatrice, relu en base ; 404 `interview_not_found` sinon."""
    row = await InterviewRepository(db, user_id).get_fresh(interview_id)
    if row is None:
        raise interview_not_found()
    return row


async def settle(db: AsyncSession, user_id: str) -> None:
    """Entretiens en cours sans session ouverte → `failed`. Sessions lues AVANT les entretiens
    (D97 n° 9). L'appelant tient `interview_lock`."""
    open_ids = await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)
    stale = [
        row
        for row in await InterviewRepository(db, user_id).running()
        if row.session_id not in open_ids.get(row.id, [])
    ]
    for row in stale:
        row.status = "failed"
        logger.info("Entretien sans session : utilisateur %s, entretien %s", user_id, row.id)
    if stale:
        await db.commit()


def interview_out(row: Interview) -> InterviewOut:
    """L'entretien pour l'API : `flags` et `cards_created` sont rangés avec le débrief."""
    data: dict[str, Any] = dict(row.debrief or {})
    flags = [str(flag) for flag in data.pop("flags", [])]
    cards_created = int(data.pop("cards_created", 0))
    return InterviewOut.model_validate(
        {
            "id": row.id,
            "application_id": row.application_id,
            "posting_id": row.posting_id,
            "role": row.role,
            "mode": row.mode,
            "duration_min": row.duration_min,
            "language": row.language,
            "session_id": row.session_id,
            "status": row.status,
            "exchanges": [ExchangeOut.model_validate(item) for item in row.exchanges],
            "debrief": DebriefOut.model_validate(data) if data else None,
            "flags": flags,
            "cards_created": cards_created,
            "created_at": row.created_at,
        }
    )


async def _launch(
    rt: ApplicationsRuntime,
    db: AsyncSession,
    user_id: str,
    setup: InterviewIn,
    *,
    application_id: str | None,
    posting_id: str | None,
    role: str | None,
) -> InterviewStartOut:
    """Contrôles d'entrée, entretien rangé, parcours lancé. Sous le verrou, dans `db`."""
    await settle(db, user_id)
    repo = InterviewRepository(db, user_id)
    if running := await repo.running():
        raise interview_in_progress(running[0].id)
    if await validated_profile(db, user_id) is None:
        raise profile_required()
    row = await repo.add(
        application_id=application_id,
        posting_id=posting_id,
        role=role,
        mode=setup.mode,
        duration_min=setup.duration_min,
        language=setup.language,
        session_id="",  # posé dès que le parcours est lancé (la colonne est obligatoire)
        status="running",
    )
    await db.commit()  # le parcours relit l'entretien dans sa propre session
    try:
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"interview_id": row.id}, subject_type=SUBJECT, subject_id=row.id
        )
    except BaseException:
        row.status = "failed"
        await db.commit()
        logger.warning("Entretien non lancé : utilisateur %s, entretien %s", user_id, row.id)
        raise
    row.session_id = session_id
    await db.commit()
    logger.info(
        "Entretien lancé : utilisateur %s, entretien %s, session %s, %s, %d min",
        user_id,
        row.id,
        session_id,
        setup.mode,
        setup.duration_min,
    )
    return InterviewStartOut(interview_id=row.id, session_id=session_id)


async def start_for_application(
    rt: ApplicationsRuntime, user_id: str, application_id: str, body: InterviewIn
) -> InterviewStartOut:
    """Lance l'entretien d'une fiche (404 `application_not_found`)."""
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        application = await get_application(db, user_id, application_id)
        return await _launch(
            rt,
            db,
            user_id,
            body,
            application_id=application.id,
            posting_id=application.posting_id,
            role=application.title,
        )


async def start_free(
    rt: ApplicationsRuntime, user_id: str, body: FreeInterviewIn
) -> InterviewStartOut:
    """Lance un entretien sans fiche, sur une offre (404 `posting_not_found`) ou un intitulé."""
    if (body.posting_id is None) == (body.role is None):
        raise invalid("posting_id", "role")  # l'un ou l'autre, jamais les deux
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        role = body.role
        if body.posting_id is not None:
            posting = await get_posting(db, user_id, body.posting_id)
            role = posting.title or DEFAULT_ROLE
        return await _launch(
            rt, db, user_id, body, application_id=None, posting_id=body.posting_id, role=role
        )


async def list_interviews(
    rt: ApplicationsRuntime, user_id: str, application_id: str | None
) -> list[InterviewOut]:
    """Les entretiens (d'une fiche), le plus récent d'abord. 404 `application_not_found` pour une
    fiche inconnue sans entretien (un entretien survit à sa fiche)."""
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        rows = await InterviewRepository(db, user_id).recent(application_id)
        if application_id is not None and not rows:
            known = await ApplicationRepository(db, user_id).get(application_id)
            if known is None:
                raise not_found()
        return [interview_out(row) for row in rows]


async def get_interview(rt: ApplicationsRuntime, user_id: str, interview_id: str) -> InterviewOut:
    async with interview_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return interview_out(await interview_row(db, user_id, interview_id))
