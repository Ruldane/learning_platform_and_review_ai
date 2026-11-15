"""Contrôle à l'entrée d'une offre (SPEC 6.3, D139) : l'offre qui entre (une offre analysée, un
lien seul) est comparée aux fiches existantes, quel que soit l'écran. Les règles sont celles de
`matching` (7.1) ; ici, la lecture de l'offre et des fiches."""

from collections.abc import Iterable
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.applications.repository import ApplicationRepository
from app.features.applications.schemas import ApplicationRef, CheckOut
from app.features.applications.service.matching import Hit, Incoming, match
from app.features.applications.service.views import alerts_out, invalid, views_of
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import get_posting
from app.features.postings.service.rules import company_key, posting_url_key


def incoming_from_posting(posting: JobPosting, distinct: Iterable[str] = ()) -> Incoming:
    """L'offre entrante : lien normalisé, entreprise et intitulé (ceux de l'offre, sinon de
    l'analyse), offres « possibles » de ses doublons, fiches confirmées « autre poste »."""
    analysis = posting.analysis or {}
    return Incoming(
        url_norm=posting.url_norm,
        company_norm=company_key(posting.company or analysis.get("company") or ""),
        title=posting.title or analysis.get("title") or "",
        posting_id=posting.id,
        possible_posting_ids=frozenset(
            str(item["posting_id"])
            for item in posting.duplicates
            if isinstance(item, dict) and item.get("level") == "possible" and item.get("posting_id")
        ),
        distinct_from=frozenset(distinct),
    )


def incoming_from_url(url: str) -> Incoming:
    """Avant l'analyse : seul le lien est connu. 422 `url` si le lien est refusé."""
    try:
        key = posting_url_key(url)
    except AppError as exc:
        if exc.code in ("invalid_url", "url_forbidden"):
            raise invalid("url") from None
        raise
    return Incoming(
        url_norm=key,
        company_norm="",
        title="",
        posting_id=None,
        possible_posting_ids=frozenset(),
    )


async def check_incoming(
    db: AsyncSession, user_id: str, incoming: Incoming, today: date
) -> list[Hit]:
    """Les fiches qui ressemblent à l'offre entrante (voir `matching.match`)."""
    views = await views_of(db, user_id, await zone_of(db, user_id))
    return match(incoming, views, today)


async def check_posting(
    db: AsyncSession, user_id: str, now: datetime, posting_id: str | None, url: str | None
) -> CheckOut:
    """`GET /applications/check` : par `posting_id` (la fiche de l'offre, les alertes et les
    informations) ou par `url` (avant l'analyse : le niveau « certain » seulement). Exactement
    une des deux entrées, sinon 422."""
    if (posting_id is None) == (url is None):
        raise invalid("posting_id", "url")
    zone = await zone_of(db, user_id)
    today = local_today(zone, now)
    own = None
    if posting_id is not None:
        posting = await get_posting(db, user_id, posting_id)
        hits = await check_incoming(db, user_id, incoming_from_posting(posting), today)
        row = await ApplicationRepository(db, user_id).by_posting(posting_id)
        if row is not None:
            own = ApplicationRef.model_validate(row, from_attributes=True)
    else:
        assert url is not None
        found = await check_incoming(db, user_id, incoming_from_url(url), today)
        hits = [hit for hit in found if hit.level == "certain"]
    alerts = await alerts_out(db, user_id, hits, zone, today)
    return CheckOut(
        own=own,
        alerts=[a for a in alerts if a.level != "info"],
        info=[a for a in alerts if a.level == "info"],
    )
