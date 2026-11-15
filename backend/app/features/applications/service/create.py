"""Création d'une fiche (SPEC 6.1 n° 2, 6.3, D139), à la main ou depuis une offre, sous le verrou
des candidatures de l'utilisatrice : contrôle des doublons, puis écriture de la fiche, de son
fil et de ses contacts dans la même transaction.

- Une fiche de cette offre existe déjà : 409 `application_exists` (`details.application_id`).
- Une fiche qui ressemble (certain, probable, possible) et que `distinct_from` ne couvre pas :
  409 `application_duplicate` (`details.alerts` : les fiches existantes, jamais l'entrée).
- Sinon 201 ; les fiches de la même entreprise des 30 derniers jours partent en `info`, et
  `distinct_from` est posé dans les deux sens (avec l'offre de chaque fiche, pour que le contrôle
  par offre se taise aussi).

Créée par une session de l'Assistant de suivi (`session_id`, 7.4), la fiche garde l'identifiant
de la session dans `ref_id` de son événement `created` : une création rejouée après un arrêt (SPEC
9.4) relit cette fiche au lieu d'en créer une seconde.

Journaux : identifiants seulement, jamais l'entreprise, l'intitulé, un contact ni une note."""

import logging
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.applications import Application
from app.db.models.postings import JobPosting
from app.features.applications.repository import (
    ApplicationRepository,
    ContactRepository,
    EventRepository,
)
from app.features.applications.schemas import AlertOut, ApplicationIn, CreatedOut
from app.features.applications.service.adopt import follows_version, freeze_version
from app.features.applications.service.check import incoming_from_posting
from app.features.applications.service.matching import Incoming, match
from app.features.applications.service.reminder_sync import sync_user
from app.features.applications.service.rules import ApplicationView, on_status
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import alerts_out, detail_out, invalid, view_of
from app.features.cv.service.versions import ready_versions_by_posting
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import get_posting
from app.features.postings.service.rules import company_key, posting_url_key

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
    """Ce qui entre dans la fiche : la copie figée de l'offre ou ce que January a saisi."""

    posting_id: str | None
    company: str
    title: str
    url: str | None
    url_norm: str | None
    text: str | None


def application_exists(application_id: str) -> AppError:
    return AppError(
        "application_exists",
        "Une fiche existe déjà pour cette offre.",
        409,
        {"application_id": application_id},
    )


def application_duplicate(alerts: list[AlertOut]) -> AppError:
    return AppError(
        "application_duplicate",
        "Cette offre ressemble à une candidature existante.",
        409,
        {"alerts": [alert.model_dump(mode="json") for alert in alerts]},
    )


def link_key(url: str | None) -> str | None:
    """La clé du lien ; 422 `url` s'il est refusé (jamais cité)."""
    if url is None:
        return None
    try:
        return posting_url_key(url)
    except AppError as exc:
        if exc.code in ("invalid_url", "url_forbidden"):
            raise invalid("url") from None
        raise


def _source(body: ApplicationIn, posting: JobPosting | None) -> Source:
    """La copie figée de l'offre (entreprise, intitulé, lien, texte) ; ce que January a saisi ne
    sert que là où l'offre ne dit rien encore. Sans `company` ou `title` : 422 `fields`."""
    analysis = (posting.analysis if posting is not None else None) or {}
    company = (posting.company if posting else None) or analysis.get("company") or body.company
    title = (posting.title if posting else None) or analysis.get("title") or body.title
    missing = [name for name, value in (("company", company), ("title", title)) if not value]
    if missing or company is None or title is None:
        raise invalid(*missing)
    url = (posting.url if posting else None) or body.url
    url_norm = (posting.url_norm if posting else None) or link_key(url)
    text = posting.text if posting else body.posting_text
    return Source(posting.id if posting else None, company, title, url, url_norm, text or None)


def _incoming(source: Source, posting: JobPosting | None, body: ApplicationIn) -> Incoming:
    """L'offre entrante, telle que la fiche sera écrite (`source` : entreprise, intitulé, lien, y
    compris ce que January a saisi pour une offre pas encore analysée) ; de l'offre, seuls
    l'identifiant et ses offres « possibles » comptent."""
    possible = incoming_from_posting(posting).possible_posting_ids if posting else frozenset()
    return Incoming(
        url_norm=source.url_norm,
        company_norm=company_key(source.company),
        title=source.title,
        posting_id=source.posting_id,
        possible_posting_ids=possible,
        distinct_from=frozenset(body.distinct_from),
    )


def _dates(body: ApplicationIn, source: Source, today: date) -> dict[str, date]:
    """Les dates posées par le statut de départ (`on_status`) ; la date de candidature donnée
    l'emporte sur celle du jour."""
    start = ApplicationView(
        id="",
        status="to_apply",
        company_norm="",
        title=source.title,
        url_norm=None,
        posting_id=None,
        applied_on=body.applied_on,
        interview_on=None,
        answered_on=None,
        created_on=today,
    )
    fields = on_status(start, body.status, today).fields()
    if body.applied_on is not None:
        fields["applied_on"] = body.applied_on
    return fields


def _joined(current: list[object], rows: list[Application]) -> list[object]:
    merged = list(current)
    for row in rows:
        for value in (row.id, row.posting_id):
            if value is not None and value not in merged:
                merged.append(value)
    return merged


def confirm_distinct(rows: list[Application], new: Application, confirmed: list[str]) -> None:
    """« C'est un autre poste » : chaque fiche confirmée et la nouvelle se désignent, par
    identifiant de fiche et par offre (le contrôle par offre se tait alors aussi)."""
    others = [row for row in rows if row.id in confirmed]
    new.distinct_from = _joined(new.distinct_from, others)
    for other in others:
        other.distinct_from = _joined(other.distinct_from, [new])


async def _link_version(db: AsyncSession, user_id: str, row: Application, now: datetime) -> None:
    """Une fiche « À postuler » suit la version prête de son offre ; une fiche créée à un autre
    statut que « Retirée » la fige (la version envoyée est celle du jour)."""
    if row.posting_id is None:
        return
    if row.status not in ("to_apply", "withdrawn"):
        await freeze_version(db, user_id, row, now)
    elif follows_version(row):
        ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
        row.cv_version_id = ready[0] if ready else None


async def _insert(
    db: AsyncSession,
    user_id: str,
    body: ApplicationIn,
    source: Source,
    when: tuple[date, datetime],
    session_id: str | None,
) -> Application:
    today, now = when
    row = await ApplicationRepository(db, user_id).add(
        posting_id=source.posting_id,
        company=source.company,
        company_norm=company_key(source.company),
        title=source.title,
        url=source.url,
        url_norm=source.url_norm,
        posting_text=source.text,
        channel=body.channel,
        status=body.status,
        notes=body.notes,
        **_dates(body, source, today),
    )
    await EventRepository(db, user_id).add(
        application_id=row.id, kind="created", at=now, status_to=body.status, ref_id=session_id
    )
    await _link_version(db, user_id, row, now)
    contacts = ContactRepository(db, user_id)
    for contact in body.contacts:
        await contacts.add(
            application_id=row.id, name=contact.name, role=contact.role, url=contact.url
        )
    return row


async def _of_session(
    db: AsyncSession, user_id: str, session_id: str | None, today: date
) -> CreatedOut | None:
    """La fiche déjà créée par cette session (rejeu), sinon `None`."""
    if session_id is None:
        return None
    known = await EventRepository(db, user_id).created_by(session_id)
    if known is None:
        return None
    row = await ApplicationRepository(db, user_id).get_fresh(known)
    return (
        None
        if row is None
        else CreatedOut(application=await detail_out(db, user_id, row, today), info=[])
    )


async def create_application(
    rt: ApplicationsRuntime, user_id: str, body: ApplicationIn, *, session_id: str | None = None
) -> CreatedOut:
    """Crée la fiche (voir le module). 404 `posting_not_found` si `posting_id` est inconnu."""
    async with rt.lock(user_id), rt.session_factory() as db:
        zone = await zone_of(db, user_id)
        now = rt.now()
        today = local_today(zone, now)
        if (again := await _of_session(db, user_id, session_id, today)) is not None:
            return again
        repo = ApplicationRepository(db, user_id)
        posting = await get_posting(db, user_id, body.posting_id) if body.posting_id else None
        if posting is not None and (known := await repo.by_posting(posting.id)) is not None:
            raise application_exists(known.id)
        source = _source(body, posting)
        rows = await repo.recent()
        hits = match(_incoming(source, posting, body), [view_of(r, zone) for r in rows], today)
        blocking = [hit for hit in hits if hit.level != "info"]
        if blocking:
            raise application_duplicate(await alerts_out(db, user_id, blocking, zone, today))
        row = await _insert(db, user_id, body, source, (today, now), session_id)
        confirm_distinct(rows, row, list(dict.fromkeys(body.distinct_from)))
        await sync_user(db, user_id, today, application_id=row.id)
        await db.commit()
        info = [hit for hit in hits if hit.level == "info"]
        logger.info("Fiche créée : utilisateur %s, fiche %s", user_id, row.id)
        return CreatedOut(
            application=await detail_out(db, user_id, row, today),
            info=await alerts_out(db, user_id, info, zone, today),
        )
