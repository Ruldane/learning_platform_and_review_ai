"""Faux port de la création d'une fiche en une phrase (`FakeApplicationStore`) en mémoire,
idempotent par session comme le contrat (D141). Aucun réseau ni LLM."""

import asyncio
from dataclasses import dataclass, field
from datetime import date

from app.agents.tools.applications_port import AlertView, InfoView, IntakeContext, IntakeDraft
from app.core.errors import AppError

TODAY = date(2026, 11, 15)
EXISTING_ID = "00000000-0000-4000-8000-0000000000a1"
OTHER_EXISTING_ID = "00000000-0000-4000-8000-0000000000a2"
ALERT_MESSAGE = (
    "You already applied for the Développeuse IA role at Société Fictive on 3 November (Applied)."
)


def alert(application_id: str = EXISTING_ID, level: str = "probable") -> AlertView:
    return AlertView(level, application_id, ALERT_MESSAGE)  # type: ignore[arg-type]


@dataclass
class FakeApplicationStore:
    today: date = TODAY
    language: str = "en"
    alerts: list[AlertView] = field(default_factory=list)
    info: list[InfoView] = field(default_factory=list)
    context_calls: int = 0
    alert_calls: list[IntakeDraft] = field(default_factory=list)
    save_calls: int = 0
    block_after_save: bool = False
    distinct_calls: list[list[str]] = field(default_factory=list)
    created: dict[str, str] = field(default_factory=dict)  # session -> fiche
    drafts: list[IntakeDraft] = field(default_factory=list)  # une par fiche créée
    refuse_with: AppError | None = None

    @property
    def saved(self) -> list[tuple[str, str, str, date | None]]:
        return [(d.company, d.title, d.status, d.applied_on) for d in self.drafts]

    async def intake_context(self, user_id: str) -> IntakeContext:
        self.context_calls += 1
        return IntakeContext(self.today, self.language)

    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]:
        self.alert_calls.append(draft)
        return list(self.alerts)

    async def intake_info(self, user_id: str, draft: IntakeDraft) -> list[InfoView]:
        return list(self.info)

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        self.save_calls += 1
        self.distinct_calls.append(list(distinct_from))
        if self.refuse_with is not None:
            raise self.refuse_with
        if session_id not in self.created:
            self.created[session_id] = f"fiche-{len(self.created) + 1}".ljust(36, "0")
            self.drafts.append(draft)
            if self.block_after_save:
                await asyncio.Event().wait()
        return self.created[session_id]
