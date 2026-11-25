"""Application kit port (`KitStore`, D142, D143) on the `applications` feature:
implementation wired by `bootstrap_agents.agent_ports(..., kit=...)`. Each call opens its own
short database sessions.

- `context`: read-only. The record (company, exact title, contact), its posting (the linked
  posting's analysis, otherwise a minimal analysis of the record's frozen copy), the validated
  master profile, the `companies` dossier if it is under 30 days old (its pages **in citation
  order**: `[n]` = rank + 1), the CV version sent when the record froze it (`version` event),
  otherwise the posting's most recent ready version, the pieces January edited (`keep`) and her
  day (time zone of her settings). 409 `posting_required` (neither posting nor frozen text), 409
  `profile_required` (no validated profile).
- `save_piece`: **idempotent per `(record, piece, session)`** and safe under parallel writes
  (the seven branches of the flow store at the same time): one lock per record, then the unique
  `(record, piece)` row; the row of the same session, or a piece January edited in the
  meantime, is never rewritten. Once the session's last piece is stored, the `kit` "finished"
  event enters the timeline, in the same transaction.
- `save_dossier`: `companies.dossier`, its pages read (in order) and its date; idempotent per
  session (the session id is stored with the dossier).

Logs: ids, numbers and statuses only, never a piece, the company, a contact or an address
(17.2)."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.kit_schema import (
    KIT_KINDS,
    CompanyDossier,
    CvVersionRef,
    KitContext,
    KitKind,
    KitStatus,
    SourceRef,
)
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.applications import Application
from app.db.models.postings import Company
from app.features.applications.repository import (
    KIT_COMPLETED_TITLE,
    CompanyRepository,
    ContactRepository,
    EventRepository,
    KitRepository,
)
from app.features.applications.service.kit_language import posting_analysis
from app.features.applications.service.reminders_out import pick_contact
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application
from app.features.cv.service.versions import (
    ready_versions_by_posting,
    validated_profile,
    version_numbers,
)
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import postings_by_ids
from app.features.postings.service.rules import company_key
from app.features.postings.service.runtime import company_lock

logger = logging.getLogger(__name__)

DOSSIER_MAX_AGE = timedelta(days=30)
GRAPH = "application_kit"
SUBJECT = "application_kit"


def company_name_key(name: str) -> str:
    """The company record key of a name: `company_key`, otherwise the lowercase name (a name
    without a Latin letter would give an empty key). A single key to read and write the dossier."""
    return company_key(name) or name.strip().casefold()


def posting_required() -> AppError:
    return AppError(
        "posting_required",
        "Add a posting or its text before preparing the application kit.",
        409,
    )


def profile_required() -> AppError:
    return AppError("profile_required", "Validate your master profile to continue.", 409)


def kit_lock(rt: ApplicationsRuntime, user_id: str, application_id: str) -> asyncio.Lock:
    """One lock per record: launch, stored pieces and edits never interleave."""
    return rt.locks.get(user_id, f"kit:{application_id}")


async def posting_inputs(
    db: AsyncSession, user_id: str, row: Application
) -> tuple[str, PostingAnalysis]:
    """The posting text (the record's frozen copy, otherwise the linked posting) and its
    analysis; 409 `posting_required` without text."""
    posting = None
    if row.posting_id is not None:
        posting = (await postings_by_ids(db, user_id, [row.posting_id])).get(row.posting_id)
    text = (row.posting_text or (posting.text if posting else "") or "").strip()
    if not text:
        raise posting_required()
    return text, posting_analysis(posting.analysis if posting else None, row, text)


def dossier_of(
    company: Company | None, now: datetime
) -> tuple[CompanyDossier | None, list[SourceRef]]:
    """The reused dossier (under `DOSSIER_MAX_AGE`, at instant `now`) and its pages, in the
    order they are cited. A single rule for the kit and the mock interview."""
    if company is None or company.dossier_at is None or not company.dossier:
        return None, []
    if now - company.dossier_at >= DOSSIER_MAX_AGE:
        return None, []
    try:
        dossier = CompanyDossier.model_validate(company.dossier)
        sources = [SourceRef.model_validate(ref) for ref in company.dossier_sources]
    except ValidationError:
        return None, []  # an unreadable dossier is redone
    return dossier, sources


class AgentKitStore:
    def __init__(self, runtime: ApplicationsRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, application_id: str) -> KitContext:
        rt = self._rt
        async with rt.session_factory() as db:
            row = await get_application(db, user_id, application_id)
            text, analysis = await posting_inputs(db, user_id, row)
            profile = await validated_profile(db, user_id)
            if profile is None:
                raise profile_required()
            today = local_today(await zone_of(db, user_id), rt.now())
            contact = pick_contact(await ContactRepository(db, user_id).of_application(row.id))
            company = await CompanyRepository(db, user_id).by_key(company_name_key(row.company))
            pieces = await KitRepository(db, user_id).of_application(row.id)
            version = await self._version(db, user_id, row)
        edited = {piece.kind for piece in pieces if piece.edited}
        dossier, sources = dossier_of(company, rt.now())
        return KitContext(
            application_id=row.id,
            language="en" if analysis.language == "en" else "fr",
            today=today,
            posting_text=text,
            analysis=analysis,
            company=row.company,
            title=row.title,
            contact=contact.name if contact else None,
            profile=profile,
            company_dossier=dossier,
            company_dossier_sources=sources,
            cv_version=version,
            keep=[kind for kind in KIT_KINDS if kind in edited],
        )

    async def _version(
        self, db: AsyncSession, user_id: str, row: Application
    ) -> CvVersionRef | None:
        """The kit's CV version: the version sent when the record froze it (`version` event),
        otherwise the posting's most recent ready version."""
        if row.cv_version_id and row.id in await EventRepository(db, user_id).version_frozen():
            number = (await version_numbers(db, user_id, [row.cv_version_id])).get(
                row.cv_version_id
            )
            if number is not None:
                return CvVersionRef(version_id=row.cv_version_id, number=number)
        if row.posting_id is None:
            return None
        ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
        return CvVersionRef(version_id=ready[0], number=ready[1]) if ready else None

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str:
        rt = self._rt
        async with kit_lock(rt, user_id, application_id), rt.session_factory() as db:
            app_row = await get_application(db, user_id, application_id)
            repo = KitRepository(db, user_id)
            row = await repo.of_kind(application_id, kind)
            if row is not None and (row.session_id == session_id or row.edited):
                # Replay (SPEC 9.4), or piece edited by January since: nothing is rewritten,
                # but the piece counts: the kit's end is written if it was the last one.
                await self._close_if_done(db, user_id, session_id, app_row)
                await db.commit()
                return row.id
            fields = {
                "status": status,
                "content": content,
                "meta": await self._meta(db, user_id, app_row, kind, meta),
                "edited": False,
                "session_id": session_id,
            }
            if row is None:
                row = await repo.add(application_id=application_id, kind=kind, **fields)
            else:
                for name, value in fields.items():
                    setattr(row, name, value)
                row.updated_at = rt.now()
            await db.flush()
            await self._close_if_done(db, user_id, session_id, app_row)
            await db.commit()
            logger.info(
                "Kit piece stored: user %s, record %s, piece %s, status %s",
                user_id,
                application_id,
                kind,
                status,
            )
            return row.id

    async def _meta(
        self, db: AsyncSession, user_id: str, row: Application, kind: str, meta: dict[str, Any]
    ) -> dict[str, Any]:
        """The piece's `meta`; the dossier keeps its pages (`source_refs`, in citation order):
        they survive a dossier redone later by another record."""
        stored = dict(meta)
        if kind != "company_brief" or not meta.get("sources"):
            return stored
        company = await CompanyRepository(db, user_id).by_key(company_name_key(row.company))
        if company is not None:
            stored["source_refs"] = [dict(ref) for ref in company.dossier_sources]
        return stored

    async def _close_if_done(
        self, db: AsyncSession, user_id: str, session_id: str, app_row: Application
    ) -> None:
        """The seven pieces are stored (by the session, or kept as they are): the `kit`
        "finished" event enters the timeline, with the count of statuses."""
        if await EventRepository(db, user_id).kit_ended(session_id):
            return
        rows = await KitRepository(db, user_id).of_application(app_row.id)
        mine = [row for row in rows if row.session_id == session_id]
        done = {row.kind for row in rows if row.session_id == session_id or row.edited}
        if done != set(KIT_KINDS):
            return
        counts = [row.status for row in mine]
        kept = len(done) - len(mine)
        text = (
            f"{KIT_COMPLETED_TITLE}: {counts.count('ready')} ready, "
            f"{counts.count('to_check')} to review, {counts.count('failed')} failed"
            + (f", {kept} kept unchanged." if kept else ".")
        )
        await EventRepository(db, user_id).add(
            application_id=app_row.id, kind="kit", at=self._rt.now(), text=text, ref_id=session_id
        )

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None:
        rt = self._rt
        key = company_name_key(company)
        async with (
            company_lock(rt.company_locks, user_id, key),
            rt.session_factory() as db,
        ):
            repo = CompanyRepository(db, user_id)
            row = await repo.by_key(key) or await repo.add(name=company[:200], name_norm=key[:200])
            if row.dossier and row.dossier.get("session_id") == session_id:
                return  # replay: nothing to rewrite
            row.dossier = {**dossier.model_dump(mode="json"), "session_id": session_id}
            row.dossier_sources = [source.model_dump(mode="json") for source in sources]
            row.dossier_at = rt.now()
            await db.commit()
            logger.info(
                "Dossier stored: user %s, company %s, session %s, %d page(s)",
                user_id,
                row.id,
                session_id,
                len(sources),
            )
