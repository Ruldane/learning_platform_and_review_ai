"""Lectures du radar (14.2, D160) : le dernier relevé, la liste et le détail. Chaque lecture corrige
d'abord un relevé `running` dont la session n'est plus ouverte (`settled`) : le statut suit la
session. Un relevé en échec porte son code (`error_code`), jamais un message."""

from datetime import datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.daily import RadarRun, RadarStatus, RadarTrigger
from app.features.radar.repository import RadarRunRepository
from app.features.radar.schemas import (
    DomainCount,
    OfferOut,
    RadarAlertOut,
    RadarDefaults,
    RadarLatestOut,
    RadarRunOut,
    RadarRunSummary,
    RunRef,
    TrendOut,
)
from app.features.radar.service.entries import is_analyzed
from app.features.radar.service.finalize import summary_of
from app.features.radar.service.runs import defaults, radar_run_not_found, settled
from app.features.radar.service.runtime import RadarRuntime

LIST_LIMIT = 20


def _ref(row: RadarRun) -> RunRef:
    return RunRef(id=row.id, created_at=row.created_at)


def summary_out(row: RadarRun) -> RadarRunSummary:
    return RadarRunSummary(
        id=row.id,
        role=row.role,
        zone=row.zone,
        status=cast(RadarStatus, row.status),
        trigger=cast(RadarTrigger, row.trigger),
        created_at=row.created_at,
        finished_at=row.finished_at,
        error_code=row.error_code,
        read_count=row.read_count,
        blocked_count=row.blocked_count,
        analyzed=row.analyzed,
        low_sample=summary_of(row).low_sample,
    )


def _offers(row: RadarRun) -> list[OfferOut]:
    """Les offres analysées, meilleur score d'abord (puis intitulé)."""
    offers = [
        OfferOut(
            url=str(entry["url"]),
            title=entry.get("title"),
            company=entry.get("company"),
            level=str(entry.get("level") or "inconnu"),
            remote=entry.get("remote"),
            salary=entry.get("salary"),
            score=int(entry.get("score") or 0),
        )
        for entry in row.postings
        if is_analyzed(entry)
    ]
    return sorted(offers, key=lambda offer: (-offer.score, offer.title or "", offer.url))


def _not_analyzed(row: RadarRun) -> int:
    """Offres lues et pas analysées : extraction en échec, ou au-delà des 50 d'un relevé."""
    return max(0, row.read_count - row.not_postings - row.analyzed)


async def run_out(db: AsyncSession, user_id: str, row: RadarRun) -> RadarRunOut:
    previous = None
    if row.previous_id is not None:
        before = await RadarRunRepository(db, user_id).get(row.previous_id)
        previous = _ref(before) if before is not None else None
    items: list[dict[str, Any]] = list(row.ranking)
    return RadarRunOut(
        **summary_out(row).model_dump(),
        not_postings=row.not_postings,
        not_analyzed=_not_analyzed(row),
        blocked_domains=[
            DomainCount(domain=domain, count=int(number))
            for domain, number in sorted(
                row.blocked_domains.items(), key=lambda pair: (-int(pair[1]), pair[0])
            )
        ],
        ranking=[TrendOut.model_validate(item) for item in items],
        alerts=[RadarAlertOut.model_validate(item) for item in row.alerts],
        offers=_offers(row),
        previous=previous,
    )


async def latest_out(rt: RadarRuntime, db: AsyncSession, user_id: str) -> RadarLatestOut:
    await settled(rt, user_id)
    repo = RadarRunRepository(db, user_id)
    running = next(iter(await repo.running()), None)
    latest = await repo.latest_finished()
    role, zone = await defaults(db, user_id)
    return RadarLatestOut(
        defaults=RadarDefaults(role=role, zone=zone),
        running=_ref(running) if running is not None else None,
        latest=await run_out(db, user_id, latest) if latest is not None else None,
    )


async def list_runs(rt: RadarRuntime, db: AsyncSession, user_id: str) -> list[RadarRunSummary]:
    await settled(rt, user_id)
    return [summary_out(row) for row in await RadarRunRepository(db, user_id).recent(LIST_LIMIT)]


async def get_run(rt: RadarRuntime, db: AsyncSession, user_id: str, run_id: str) -> RadarRunOut:
    await settled(rt, user_id)
    row = await RadarRunRepository(db, user_id).get_fresh(run_id)
    if row is None:
        raise radar_run_not_found()
    return await run_out(db, user_id, row)


async def offers_since(
    db: AsyncSession, user_id: str, since: datetime | None
) -> list[dict[str, Any]]:
    """Les offres analysées et notées des relevés finis (`done`) après `since` ; sans `since`
    (aucun brief avant), celles du dernier relevé fini seulement. Pour le brief du jour (P9) : une
    entrée par offre, `{run_id, url_key, url, title, company, score}`, relevé le plus récent
    d'abord, lien jamais lu ni journalisé ici."""
    repo = RadarRunRepository(db, user_id)
    if since is None:
        latest = await repo.latest_done()
        runs = [latest] if latest is not None else []
    else:
        runs = await repo.done_since(since)
    return [
        {
            "run_id": run.id,
            "url_key": str(entry["key"]),
            "url": str(entry["url"]),
            "title": entry.get("title"),
            "company": entry.get("company"),
            "score": entry["score"],
        }
        for run in runs
        for entry in run.postings
        if is_analyzed(entry) and entry.get("key") and isinstance(entry.get("score"), int)
    ]
