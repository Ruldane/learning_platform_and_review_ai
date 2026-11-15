"""Le comité de recrutement simulé côté API (SPEC F19, D147) : lancement du parcours
`hiring_committee` sur une version de CV prête, liste et détail avec l'avant et l'après.

- Un seul comité ouvert par offre (409 `committee_in_progress`, `details.run_id`), sous le verrou
  des comités de l'utilisatrice ; l'exécution est rangée (`running`) AVANT le lancement : le
  parcours la relit dans sa propre session. Un lancement refusé par le moteur la passe en `failed`.
  `previous_id` : la dernière exécution `done` de l'offre, fixée au lancement (aucune exécution de
  la même offre ne tourne en parallèle).
- Le statut suit l'issue de la session (comme D129 n° 5) : une exécution `running` dont la session
  n'est plus ouverte (panne, délai, annulation) passe en `failed` à la lecture suivante, sous le
  verrou ; une session terminée ne reprend jamais, la correction est sûre. `done` est posé par le
  port (`committee_store`).
- `previous` (« avant et après », F19) : le diff avec `previous_id`, calculé à la lecture
  (`committee_diff`), seulement pour une exécution terminée.

Journaux : identifiants et statuts seulement, jamais le CV, l'offre ni une parole."""

import asyncio
import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.committee_schema import PersonaVote
from app.core.errors import AppError
from app.db.models.applications import CommitteeRun
from app.features.applications.repository import ApplicationRepository
from app.features.applications.repository_committee import CommitteeRepository
from app.features.applications.schemas_committee import (
    ChangeOut,
    CommitteeIn,
    CommitteeRunOut,
    CommitteeStartOut,
    ObjectionOut,
    VoteOut,
)
from app.features.applications.service.committee_diff import committee_diff
from app.features.applications.service.kit_store import profile_required
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.review_data import version_not_found
from app.features.cv.service.versions import validated_profile, version_ref
from app.features.postings.service.queries import get_posting
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

GRAPH = "hiring_committee"
SUBJECT = "committee_run"


def committee_not_found() -> AppError:
    return AppError("committee_not_found", "Exécution du comité introuvable.", 404)


def committee_in_progress(run_id: str) -> AppError:
    return AppError(
        "committee_in_progress",
        "Le comité de cette offre est déjà réuni : attends la fin de sa session.",
        409,
        {"run_id": run_id},
    )


def version_not_ready() -> AppError:
    return AppError(
        "version_not_ready",
        "Cette version du CV n'est pas prête : attends la fin de son rendu.",
        409,
    )


def committee_lock(rt: ApplicationsRuntime, user_id: str) -> asyncio.Lock:
    """Un verrou par utilisatrice : lancement, résultat rangé et lecture ne se croisent pas."""
    return rt.locks.get(user_id, "committee")


async def committee_row(db: AsyncSession, user_id: str, run_id: str) -> CommitteeRun:
    """L'exécution de l'utilisatrice, relue en base ; 404 `committee_not_found` sinon."""
    row = await CommitteeRepository(db, user_id).get_fresh(run_id)
    if row is None:
        raise committee_not_found()
    return row


async def settle(db: AsyncSession, user_id: str) -> None:
    """Exécutions en cours sans session ouverte → `failed`. Sessions lues AVANT les exécutions
    (D97 n° 9). L'appelant tient `committee_lock`."""
    open_ids = await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)
    stale = [
        row
        for row in await CommitteeRepository(db, user_id).running()
        if row.session_id not in open_ids.get(row.id, [])
    ]
    for row in stale:
        row.status = "failed"
        logger.info("Comité sans session : utilisateur %s, exécution %s", user_id, row.id)
    if stale:
        await db.commit()


def _votes_of(row: CommitteeRun) -> list[PersonaVote]:
    return [PersonaVote.model_validate(item) for item in row.votes]


def _objection_texts(row: CommitteeRun) -> list[str]:
    return [str(item["text"]) for item in row.objections]


def run_out(row: CommitteeRun, previous: CommitteeRun | None) -> CommitteeRunOut:
    """L'exécution pour l'API ; `previous` : celle de `previous_id`, si elle existe encore. Le
    diff n'est calculé que pour deux exécutions terminées."""
    diff = None
    if row.status == "done" and previous is not None and previous.status == "done":
        diff = committee_diff(
            previous.id,
            _votes_of(previous),
            _votes_of(row),
            _objection_texts(previous),
            _objection_texts(row),
        )
    return CommitteeRunOut(
        id=row.id,
        cv_version_id=row.cv_version_id,
        posting_id=row.posting_id,
        application_id=row.application_id,
        session_id=row.session_id,
        status=row.status,  # type: ignore[arg-type]  # colonne texte, valeurs de `RunStatus`
        votes=[VoteOut.model_validate(item) for item in row.votes],
        verdict=row.verdict,  # type: ignore[arg-type]  # idem, valeurs de `Verdict`
        objections=[ObjectionOut.model_validate(item) for item in row.objections],
        changes=[ChangeOut.model_validate(item) for item in row.changes],
        previous=diff,
        created_at=row.created_at,
    )


async def _launch(
    rt: ApplicationsRuntime, db: AsyncSession, user_id: str, row: CommitteeRun
) -> str:
    """Lance le parcours sur l'exécution rangée ; refusé, elle passe en `failed`."""
    try:
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"run_id": row.id}, subject_type=SUBJECT, subject_id=row.id
        )
    except Exception:
        row.status = "failed"
        await db.commit()
        logger.warning("Comité non lancé : utilisateur %s, exécution %s", user_id, row.id)
        raise
    row.session_id = session_id
    await db.commit()
    return session_id


async def start_committee(
    rt: ApplicationsRuntime, user_id: str, body: CommitteeIn
) -> CommitteeStartOut:
    """Lance le comité sur la version de CV. 404 `version_not_found`, 409 `version_not_ready`,
    409 `committee_in_progress`, 409 `profile_required`, 404 `posting_not_found`."""
    async with committee_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        ref = await version_ref(db, user_id, body.cv_version_id)
        if ref is None:
            raise version_not_found()
        posting_id, status = ref
        if status != "ready":
            raise version_not_ready()
        repo = CommitteeRepository(db, user_id)
        if running := await repo.running(posting_id):
            raise committee_in_progress(running[0].id)
        if await validated_profile(db, user_id) is None:
            raise profile_required()
        await get_posting(db, user_id, posting_id)
        application = await ApplicationRepository(db, user_id).by_posting(posting_id)
        previous = await repo.last_done(posting_id)
        row = await repo.add(
            cv_version_id=body.cv_version_id,
            posting_id=posting_id,
            application_id=application.id if application else None,
            session_id="",  # posé dès que le parcours est lancé (la colonne est obligatoire)
            status="running",
            previous_id=previous.id if previous else None,
        )
        await db.commit()  # le parcours relit l'exécution dans sa propre session
        session_id = await _launch(rt, db, user_id, row)
    logger.info(
        "Comité lancé : utilisateur %s, exécution %s, session %s, version %s",
        user_id,
        row.id,
        session_id,
        body.cv_version_id,
    )
    return CommitteeStartOut(run_id=row.id, session_id=session_id)


async def _outs(
    db: AsyncSession, user_id: str, rows: Sequence[CommitteeRun]
) -> list[CommitteeRunOut]:
    wanted = {row.previous_id for row in rows if row.previous_id}
    previous = await CommitteeRepository(db, user_id).by_ids(wanted)
    return [run_out(row, previous.get(row.previous_id or "")) for row in rows]


async def list_runs(
    rt: ApplicationsRuntime, user_id: str, posting_id: str | None
) -> list[CommitteeRunOut]:
    """Les exécutions (d'une offre), la plus récente d'abord, chacune avec son avant et après."""
    async with committee_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return await _outs(db, user_id, await CommitteeRepository(db, user_id).recent(posting_id))


async def get_run(rt: ApplicationsRuntime, user_id: str, run_id: str) -> CommitteeRunOut:
    async with committee_lock(rt, user_id), rt.session_factory() as db:
        await settle(db, user_id)
        [out] = await _outs(db, user_id, [await committee_row(db, user_id, run_id)])
        return out
