"""Registre des passages planifiés (P13, D158) : `claim` atomique, `finish`, `fail`, lectures.

Un passage se range par `(utilisateur, tâche, période)` (`periods`). `claim` gagne la période
(insertion sans conflit) ou reprend un passage `failed` ou `running` périmé (30 minutes), 3 essais
au plus ; `done` et `skipped` ne se reprennent jamais. Le commit appartient à l'appelant : il
valide juste après `claim`. Journaux : identifiants, nombres et codes seulement."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.daily import JobRun, JobStatus
from app.features.ledger.repository import JobRunRepository, all_user_ids
from app.features.ledger.service.periods import MAX_ATTEMPTS, is_stale

logger = logging.getLogger(__name__)

GENERIC_CODE = "error"
_CODE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")


@dataclass(frozen=True)
class Claim:
    run_id: str
    attempt: int


@dataclass(frozen=True)
class JobRunView:
    run_id: str
    name: str
    period: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    attempts: int
    error_code: str | None
    ref_id: str | None
    next_due_at: datetime | None


def _view(row: JobRun) -> JobRunView:
    return JobRunView(
        run_id=row.id,
        name=row.name,
        period=row.period,
        status=cast(JobStatus, row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        attempts=row.attempts,
        error_code=row.error_code,
        ref_id=row.ref_id,
        next_due_at=row.next_due_at,
    )


def safe_code(code: str) -> str:
    """Un code d'erreur (type d'exception ou code d'`AppError`) ; tout autre texte (un message
    peut citer une donnée) est remplacé par `error`."""
    return code if _CODE.fullmatch(code) else GENERIC_CODE


async def claim(
    db: AsyncSession, user_id: str, name: str, period: str, now: datetime
) -> Claim | None:
    """Gagne le passage `(name, period)` ou rend `None` (déjà gagné, fini, en cours non périmé
    ou sans essai restant). À valider tout de suite par l'appelant."""
    repo = JobRunRepository(db, user_id)
    created = await repo.insert_running(name, period, now)
    if created is not None:
        logger.debug("Registre : passage %s gagné (essai 1)", created)
        return Claim(created, 1)
    row = await repo.by_period(name, period)
    if row is None or row.status in ("done", "skipped"):
        return None
    if row.status == "running" and not is_stale(row.started_at, now):
        return None
    run_id, old = row.id, row.attempts  # lus avant l'UPDATE, qui met à jour l'objet de la session
    if old >= MAX_ATTEMPTS:
        if row.status == "running" and await repo.abandon(run_id, old, now):
            logger.warning("Registre : passage %s abandonné après %d essais", run_id, old)
        return None
    if not await repo.reclaim(run_id, old, now):
        return None
    logger.info("Registre : passage %s repris (essai %d)", run_id, old + 1)
    return Claim(run_id, old + 1)


async def finish(
    db: AsyncSession,
    user_id: str,
    run_id: str,
    *,
    attempt: int,
    status: Literal["done", "skipped"],
    now: datetime,
    ref_id: str | None = None,
    next_due_at: datetime | None = None,
) -> None:
    """Termine l'essai `attempt` (celui du `Claim`) : un ouvrier périmé, dont le passage a été
    repris depuis (essai suivant), ne ferme rien."""
    done = await JobRunRepository(db, user_id).close_running(
        run_id, attempt, now, status=status, ref_id=ref_id, next_due_at=next_due_at, error_code=None
    )
    if done:
        logger.debug("Registre : passage %s terminé (%s)", run_id, status)
    else:
        logger.info("Registre : passage %s, essai %d déjà clos ou repris", run_id, attempt)


async def fail(
    db: AsyncSession, user_id: str, run_id: str, *, attempt: int, code: str, now: datetime
) -> None:
    """Met en échec l'essai `attempt` (voir `finish`)."""
    code = safe_code(code)
    failed = await JobRunRepository(db, user_id).close_running(
        run_id, attempt, now, status="failed", error_code=code
    )
    if failed:
        logger.warning("Registre : passage %s en échec (%s)", run_id, code)
    else:
        logger.info("Registre : passage %s, essai %d déjà clos ou repris", run_id, attempt)


async def reopen(
    db: AsyncSession, user_id: str, view: JobRunView, *, code: str, now: datetime
) -> bool:
    """Un passage `done` dont le travail lancé a échoué repasse en `failed` : il compte comme non
    fait, `claim` le reprend (3 essais au plus, comme tout passage en échec)."""
    reopened = await JobRunRepository(db, user_id).reopen_done(
        view.run_id, view.attempts, now, safe_code(code)
    )
    if reopened:
        logger.warning("Registre : passage %s rouvert (%s)", view.run_id, safe_code(code))
    return reopened


async def last_done(db: AsyncSession, user_id: str, name: str) -> JobRunView | None:
    row = await JobRunRepository(db, user_id).last_done(name)
    return _view(row) if row is not None else None


async def recent_failures(
    db: AsyncSession, user_id: str, since: datetime | None, limit: int
) -> list[JobRunView]:
    """Les passages en échec (plus récents d'abord), pour le fil d'activité."""
    return [_view(row) for row in await JobRunRepository(db, user_id).failures(since, limit)]


async def user_ids(db: AsyncSession) -> list[str]:
    """SEULE lecture sans `user_id` du registre (comme D18, D91) : les comptes, pour les tâches
    planifiées."""
    return await all_user_ids(db)
