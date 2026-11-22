"""Un aperçu scelle la source et le créneau. Seule sa confirmation écrit chez Google."""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import new_id
from app.features.calendar.repository import Proposals
from app.features.calendar.schemas import CalendarProposalOut, InterviewSelection, Selection
from app.features.calendar.service.availability import overlaps
from app.features.calendar.service.oauth import Credential, credential
from app.features.calendar.service.runtime import CalendarRuntime
from app.features.calendar.service.slots import interview_period, study_period
from app.features.calendar.service.sources import Source, read_source
from app.providers.calendar.base import CalendarEvent, Interval, conflict, same_event

SELECTION = TypeAdapter[Selection](Selection)
PROPOSAL_TTL = timedelta(minutes=10)


def _event_id(user_id: str, selection: Selection) -> str:
    return sha256(
        f"tremplin:agenda:v1:{user_id}:{selection.kind}:{selection.source_id}".encode()
    ).hexdigest()


def _source_hash(source: Source, selection: Selection) -> str:
    contents = [
        source.title,
        source.day.isoformat(),
        source.minutes,
        source.zone.key,
        SELECTION.dump_python(selection, mode="json"),
    ]
    return sha256(json.dumps(contents, ensure_ascii=False).encode()).hexdigest()


def _event_stamp(event: CalendarEvent | None) -> str | None:
    if event is None:
        return None
    data = [
        event.title,
        event.period.start.astimezone(UTC).isoformat(),
        event.period.end.astimezone(UTC).isoformat(),
    ]
    return sha256(json.dumps(data).encode()).hexdigest()


def stale() -> AppError:
    return AppError(
        "calendar_proposal_stale", "Refais un aperçu de ce créneau avant de confirmer.", 409
    )


async def require_credential(rt: CalendarRuntime, db: AsyncSession, user_id: str) -> Credential:
    rt.provider()
    active = await credential(rt, db, user_id)
    if active is None:
        raise AppError("calendar_disconnected", "Connecte Google Agenda pour continuer.", 409)
    return active


async def prepare(rt: CalendarRuntime, user_id: str, selection: Selection) -> CalendarProposalOut:
    async with rt.lock(user_id):
        async with rt.factory() as db:
            active = await require_credential(rt, db, user_id)
            source = await read_source(db, user_id, selection)
        port = rt.provider()
        access = await port.access(active.refresh)
        now, event_id = rt.now(), _event_id(user_id, selection)
        old = await port.event(access, event_id)
        if isinstance(selection, InterviewSelection):
            period = interview_period(source, selection, now)
            if (old is None or old.period != period) and any(
                overlaps(period, block) for block in await port.busy(access, period)
            ):
                raise conflict()
        else:
            period = await study_period(port, access, source, now, old)
        event = CalendarEvent(event_id, source.title, period, source.zone.key)
        action: Literal["add", "update", "unchanged"] = (
            "add" if old is None else ("unchanged" if same_event(old, event) else "update")
        )
        preview = CalendarProposalOut(
            id=new_id(),
            status="proposed",
            action=action,
            kind=selection.kind,
            title=event.title,
            start=period.start,
            end=period.end,
            timezone=event.timezone,
        )
        async with rt.factory() as db:
            await Proposals(db, user_id).add(
                id=preview.id,
                connection_generation=active.generation,
                source_hash=_source_hash(source, selection),
                expires_at=now + PROPOSAL_TTL,
                starts_at=preview.start.astimezone(UTC),
                event_id=event_id,
                payload={
                    "preview": preview.model_dump(mode="json"),
                    "selection": SELECTION.dump_python(selection, mode="json"),
                    "previous": _event_stamp(old),
                },
            )
            await db.commit()
        return preview


async def confirm(rt: CalendarRuntime, user_id: str, proposal_id: str) -> CalendarProposalOut:
    async with rt.lock(user_id):
        async with rt.factory() as db:
            row = await Proposals(db, user_id).get(proposal_id)
            if row is None:
                raise AppError("calendar_proposal_not_found", "Aperçu Agenda introuvable.", 404)
            preview = CalendarProposalOut.model_validate(row.payload["preview"])
            result = preview.model_copy(update={"status": "synced"})
            if row.synced_at is not None:
                return result
            active = await require_credential(rt, db, user_id)
            now = rt.now()
            if (
                row.connection_generation != active.generation
                or row.expires_at <= now
                or preview.start <= now - timedelta(minutes=1)
            ):
                raise stale()
            selection = SELECTION.validate_python(row.payload["selection"])
            source = await read_source(db, user_id, selection)
            if row.source_hash != _source_hash(source, selection):
                raise stale()
            event_id, previous = row.event_id, row.payload.get("previous")
        await _sync(rt, active, preview, event_id, previous, now)
        async with rt.factory() as db:
            repo = Proposals(db, user_id)
            row = await repo.get(proposal_id)
            if row is not None:
                await repo.supersede(row)
                row.synced_at = rt.now()
                await db.commit()
        return result


async def _sync(
    rt: CalendarRuntime,
    active: Credential,
    preview: CalendarProposalOut,
    event_id: str,
    previous: str | None,
    now: datetime,
) -> None:
    port = rt.provider()
    period = Interval(preview.start, preview.end)
    event = CalendarEvent(event_id, preview.title, period, preview.timezone)
    access = await port.access(active.refresh)
    old = await port.event(access, event.id)
    if old is not None and same_event(old, event):
        return
    if preview.start < now or _event_stamp(old) != previous:
        # L’aperçu ne couvre plus l’événement courant ou son créneau.
        raise stale()
    if preview.action == "unchanged":
        raise stale()
    if (old is None or old.period != period) and any(
        overlaps(period, block) for block in await port.busy(access, period)
    ):
        raise conflict()
    await port.upsert(access, event, previous=old)
