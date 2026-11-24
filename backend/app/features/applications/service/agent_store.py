"""Port for creating a record from one sentence (`ApplicationStore`, D141) on the `applications`
feature: implementation wired by `bootstrap_agents.agent_ports(..., applications=...)`. Each call
opens its own short database sessions.

- `intake_context`: January's day (time zone from her settings) and her interface language.
- `intake_alerts`: the same rules as manual creation (`match`, 7.1) on January's records, without
  the plain information ("same company within 30 days"); the record being prepared has neither
  link nor posting, only the company and job title count.
- `intake_info`: the plain information only, which the session announces on creation (M4); a
  failed read returns it empty (log: the error type).
- `save_intake`: `create_application` (the service behind `POST /applications`: same duplicate
  check, same lock, same timeline), idempotent per session (`ref_id` of the `created` event);
  `distinct_from`: the alert's records that January confirmed as "another position".

Logs: ids only, never the sentence, the company, the job title or a contact."""

import logging
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.applications_port import (
    AlertStrength,
    AlertView,
    InfoView,
    IntakeContext,
    IntakeDraft,
)
from app.core.clock import local_today
from app.features.applications.repository import ApplicationRepository, user_language
from app.features.applications.schemas import AlertOut, ApplicationIn, ContactIn
from app.features.applications.service.create import create_application
from app.features.applications.service.matching import Incoming, match
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import alerts_out, view_of
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.rules import company_key

logger = logging.getLogger(__name__)


def application_in(draft: IntakeDraft, distinct_from: list[str]) -> ApplicationIn:
    """The confirmed record, as the `POST /applications` route receives it."""
    contacts = (
        [ContactIn(name=draft.contact_name, role=draft.contact_role)] if draft.contact_name else []
    )
    return ApplicationIn(
        company=draft.company,
        title=draft.title,
        status=draft.status,
        applied_on=draft.applied_on,
        channel=draft.channel,
        notes=draft.notes,
        contacts=contacts,
        distinct_from=distinct_from,
    )


class AgentApplicationStore:
    def __init__(self, runtime: ApplicationsRuntime) -> None:
        self._rt = runtime

    @property
    def _factory(self) -> async_sessionmaker[AsyncSession]:
        return self._rt.session_factory

    async def intake_context(self, user_id: str) -> IntakeContext:
        async with self._factory() as db:
            zone = await zone_of(db, user_id)
            language = await user_language(db, user_id)
        return IntakeContext(local_today(zone, self._rt.now()), language)

    async def _alerts(self, user_id: str, draft: IntakeDraft, *, info: bool) -> list[AlertOut]:
        """The look-alike records (plain information only, or without it)."""
        incoming = Incoming(
            url_norm=None,
            company_norm=company_key(draft.company),
            title=draft.title,
            posting_id=None,
            possible_posting_ids=frozenset(),
        )
        async with self._factory() as db:
            zone = await zone_of(db, user_id)
            today = local_today(zone, self._rt.now())
            rows = await ApplicationRepository(db, user_id).recent()
            hits = match(incoming, [view_of(row, zone) for row in rows], today)
            kept = [hit for hit in hits if (hit.level == "info") == info]
            return await alerts_out(db, user_id, kept, zone, today)

    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]:
        alerts = await self._alerts(user_id, draft, info=False)
        return [
            AlertView(cast(AlertStrength, alert.level), alert.application_id, alert.message)
            for alert in alerts
        ]

    async def intake_info(self, user_id: str, draft: IntakeDraft) -> list[InfoView]:
        """The plain information; a failed read returns it empty (the record is created anyway),
        the log only states the error type."""
        try:
            alerts = await self._alerts(user_id, draft, info=True)
        except Exception as exc:  # noqa: BLE001 - one piece of information less does not hold the record
            logger.warning(
                "Intake information not read: user %s, %s",
                user_id,
                type(exc).__name__,
            )
            return []
        return [InfoView(a.application_id, a.company, a.title, a.status, a.message) for a in alerts]

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        created = await create_application(
            self._rt, user_id, application_in(draft, distinct_from), session_id=session_id
        )
        return created.application.id
