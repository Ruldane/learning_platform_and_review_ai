"""Lien version de CV ↔ candidature (SPEC 6.1 n° 1, D139). Une offre qui a une version de CV
prête et aucune fiche reçoit sa fiche « À postuler » ; tant que la fiche n'a pas quitté
« À postuler », `cv_version_id` suit la version prête la plus récente ; à la première sortie de
« À postuler » vers tout statut sauf « Retirée », elle fige la version envoyée (événement
`version`) : une nouvelle version ne la remplace plus, même si la fiche revient à « À postuler »
puis repasse à « Postulée ». Idempotent : une offre qui a déjà une
fiche, quel que soit son statut (« Retirée » comprise), n'en reçoit pas une seconde.

Une fiche sans offre (saisie à la main ou en une phrase) qui ressemble à l'offre (`adopt_link`,
D155) est **reliée** au lieu de recevoir une seconde fiche : « À postuler », elle suit la version
prête ; déjà postulée, elle la fige (événement « liée à la fiche »). Une offre qui ressemble à une
fiche déjà liée, ou « possible », ne reçoit aucune fiche : l'alerte de sa page reste le chemin.
Le CV (`cv`) n'importe jamais ce module : c'est la candidature qui lit les versions."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.db.models.applications import Application
from app.db.models.postings import JobPosting
from app.features.applications.repository import ApplicationRepository, EventRepository
from app.features.applications.service.adopt_link import link_posting, target_of
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.versions import ready_versions_by_posting
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import postings_by_ids
from app.features.postings.service.rules import company_key
from app.features.postings.service.runtime import utc_now

logger = logging.getLogger(__name__)

UNKNOWN_COMPANY = "Entreprise non précisée"
UNKNOWN_TITLE = "Poste non précisé"


def follows_version(row: Application) -> bool:
    """La fiche suit la version prête la plus récente : jamais postulée."""
    return row.status == "to_apply" and row.applied_on is None


async def freeze_version(
    db: AsyncSession, user_id: str, row: Application, at: datetime, *, linked: bool = False
) -> None:
    """À la première sortie de « À postuler » (voir `events`) : la fiche garde la version prête la
    plus récente de son offre (événement `version`) ; sans version prête, celle qu'elle suivait.
    Une version déjà figée (événement `version`) n'est jamais remplacée. `linked` : la fiche déjà
    postulée vient d'être reliée à son offre, la version peut être postérieure à la candidature :
    l'événement dit « liée à la fiche », pas « envoyée »."""
    if row.posting_id is None or row.id in await EventRepository(db, user_id).version_frozen():
        return
    ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
    if ready is None:
        return
    row.cv_version_id = ready[0]
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="version",
        at=at,
        text=f"Version {ready[1]} du CV {'liée à la fiche' if linked else 'envoyée'}.",
        ref_id=ready[0],
    )


async def _link(
    db: AsyncSession, user_id: str, row: Application, posting: JobPosting, ready: tuple[str, int]
) -> None:
    """Relie la fiche sans offre à l'offre dont la version est prête (voir `adopt_link`) : une
    fiche « À postuler » suit la version prête, une fiche déjà postulée la fige."""
    link_posting(row, posting)
    if row.status not in ("to_apply", "withdrawn"):
        await freeze_version(db, user_id, row, utc_now(), linked=True)
    elif follows_version(row):
        row.cv_version_id = ready[0]
    logger.info("Fiche reliée à une offre : utilisateur %s, fiche %s", user_id, row.id)


async def _create(db: AsyncSession, user_id: str, posting: JobPosting, version_id: str) -> None:
    analysis = posting.analysis or {}
    company = posting.company or analysis.get("company") or UNKNOWN_COMPANY
    row = await ApplicationRepository(db, user_id).add(
        posting_id=posting.id,
        company=company,
        company_norm=company_key(company),
        title=posting.title or analysis.get("title") or UNKNOWN_TITLE,
        url=posting.url,
        url_norm=posting.url_norm,
        posting_text=posting.text,
        status="to_apply",
        cv_version_id=version_id,
    )
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="created",
        at=utc_now(),
        status_to="to_apply",
        ref_id=version_id,
    )


async def adopt_versions(db: AsyncSession, user_id: str) -> int:
    """Crée les fiches des offres qui ont une version prête et aucune fiche, fait suivre leur
    version aux fiches « À postuler » ; rend le nombre de fiches créées. Le commit appartient à
    l'appelant, qui tient le verrou des candidatures (`adopt`)."""
    ready = await ready_versions_by_posting(db, user_id)
    if not ready:
        return 0
    repo = ApplicationRepository(db, user_id)
    existing = await repo.by_postings(ready.keys())
    missing = [posting_id for posting_id in ready if posting_id not in existing]
    frozen = await EventRepository(db, user_id).version_frozen()
    for posting_id, row in existing.items():
        if (
            follows_version(row)
            and row.id not in frozen
            and row.cv_version_id != ready[posting_id][0]
        ):
            row.cv_version_id = ready[posting_id][0]
    postings = await postings_by_ids(db, user_id, missing)
    zone = await zone_of(db, user_id)
    today = local_today(zone, utc_now())
    rows = await repo.recent()
    created = 0
    for posting_id in missing:
        posting = postings.get(posting_id)
        if posting is None:
            continue
        target, similar = target_of(posting, rows, zone, today)
        if target is not None:
            await _link(db, user_id, target, posting, ready[posting_id])
        elif not similar:
            await _create(db, user_id, posting, ready[posting_id][0])
            created += 1
    await db.flush()
    if created:
        logger.info("Fiches créées par les versions de CV : utilisateur %s, %d", user_id, created)
    return created


async def adopt(rt: ApplicationsRuntime, user_id: str) -> int:
    """`adopt_versions` sous le verrou des candidatures, dans sa propre transaction (validée) :
    appelée en tête de la liste, des indicateurs et de la tâche planifiée."""
    async with rt.lock(user_id), rt.session_factory() as db:
        created = await adopt_versions(db, user_id)
        await db.commit()
        return created
