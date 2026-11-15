"""Port de la création d'une fiche en une phrase (`ApplicationStore`, D141) sur la feature
`applications` : implémentation branchée par `bootstrap_agents.agent_ports(..., applications=...)`.
Chaque appel ouvre ses propres sessions de base, courtes.

- `intake_context` : le jour de January (fuseau de ses réglages) et la langue de son interface.
- `intake_alerts` : les mêmes règles que la création à la main (`match`, 7.1) sur les fiches de
  January, sans les simples informations (« même entreprise dans les 30 jours ») ; la fiche en
  préparation n'a ni lien ni offre, seuls l'entreprise et l'intitulé comptent.
- `intake_info` : les simples informations seules, que la session annonce à la création (M4).
- `save_intake` : `create_application` (le service de `POST /applications` : même contrôle des
  doublons, même verrou, même fil), idempotent par session (`ref_id` de l'événement `created`) ;
  `distinct_from` : les fiches de l'alerte que January a confirmées « autre poste ».

Journaux : identifiants seulement, jamais la phrase, l'entreprise, l'intitulé ni un contact."""

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


def application_in(draft: IntakeDraft, distinct_from: list[str]) -> ApplicationIn:
    """La fiche confirmée, telle que la route `POST /applications` la reçoit."""
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
        """Les fiches qui ressemblent (les simples informations seules, ou sans elles)."""
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
        return [
            InfoView(a.application_id, a.company, a.title, a.status, a.message)
            for a in await self._alerts(user_id, draft, info=True)
        ]

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        created = await create_application(
            self._rt, user_id, application_in(draft, distinct_from), session_id=session_id
        )
        return created.application.id
