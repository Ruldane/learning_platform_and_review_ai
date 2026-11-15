"""Lien version de CV ↔ candidature (SPEC 6.1 n° 1, D139). Une offre qui a une version de CV
prête et aucune fiche reçoit sa fiche « À postuler » ; tant que la fiche n'a pas été postulée,
`cv_version_id` suit la version prête la plus récente ; passée à « Postulée », elle fige la
version envoyée (une nouvelle version ne la remplace plus). Idempotent : une offre qui a déjà une
fiche, quel que soit son statut (« Retirée » comprise), n'en reçoit pas une seconde. Le CV
(`cv`) n'importe jamais ce module : c'est la candidature qui lit les versions."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.applications import Application
from app.features.applications.repository import ApplicationRepository, EventRepository
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.versions import ready_versions_by_posting
from app.features.postings.service.queries import postings_by_ids
from app.features.postings.service.rules import company_key
from app.features.postings.service.runtime import utc_now

logger = logging.getLogger(__name__)

UNKNOWN_COMPANY = "Entreprise non précisée"
UNKNOWN_TITLE = "Poste non précisé"


def follows_version(row: Application) -> bool:
    """La fiche suit la version prête la plus récente : jamais postulée."""
    return row.status == "to_apply" and row.applied_on is None


async def freeze_version(db: AsyncSession, user_id: str, row: Application, at: datetime) -> None:
    """À « Postulée » pour la première fois : la fiche garde la version prête la plus récente de
    son offre (événement `version`) ; sans version prête, elle garde celle qu'elle suivait."""
    if row.posting_id is None:
        return
    ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
    if ready is None:
        return
    row.cv_version_id = ready[0]
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="version",
        at=at,
        text=f"Version {ready[1]} du CV envoyée.",
        ref_id=ready[0],
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
    for posting_id, row in existing.items():
        if follows_version(row) and row.cv_version_id != ready[posting_id][0]:
            row.cv_version_id = ready[posting_id][0]
    postings = await postings_by_ids(db, user_id, missing)
    created = 0
    for posting_id in missing:
        posting = postings.get(posting_id)
        if posting is None:
            continue
        analysis = posting.analysis or {}
        company = posting.company or analysis.get("company") or UNKNOWN_COMPANY
        row = await repo.add(
            posting_id=posting_id,
            company=company,
            company_norm=company_key(company),
            title=posting.title or analysis.get("title") or UNKNOWN_TITLE,
            url=posting.url,
            url_norm=posting.url_norm,
            posting_text=posting.text,
            status="to_apply",
            cv_version_id=ready[posting_id][0],
        )
        await EventRepository(db, user_id).add(
            application_id=row.id,
            kind="created",
            at=utc_now(),
            status_to="to_apply",
            ref_id=ready[posting_id][0],
        )
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
