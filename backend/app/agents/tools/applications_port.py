"""Port for creating an application from one sentence (SPEC 6.1, 6.3, D141). `app.agents` imports
no feature (contract 6): it describes here what the `application_intake` flow needs (January's day,
the duplicate alerts of an application being drafted, the creation); the `applications` feature
implements it (`AgentApplicationStore`, `service/agent_store.py`).

January's sentence and the application it describes are personal data: neither here nor in the
implementation are they logged (17.2).

- `intake_alerts`: same rules as manual creation (`match`, 7.1), **without** the plain notices
  ("same company within 30 days") that block nothing; applications are returned from the
  strongest alert to the weakest.
- `intake_info`: the same applications, but only the plain notices ("same company within
  30 days", SPEC 6.3): they block nothing, the session announces them at creation.
- `save_intake`: creation goes through the service of the `POST /applications` route (same
  duplicate check: without a `distinct_from` covering them, a similar application is refused) and
  is **idempotent per session**: a node replayed after a stop (SPEC 9.4) does not create a second
  application, it reads back the id of the session's one.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.errors import AppError
from app.db.models.applications import ApplicationStatus, Channel

AlertStrength = Literal["certain", "probable", "possible"]
COMPANY_MAX = 200
TITLE_MAX = 200
CONTACT_MAX = 120
NOTES_MAX = 500


class IntakeDraft(BaseModel):
    """The application January's sentence describes: structured output of the tracking Assistant,
    then what January confirms. An empty optional field means "absent"; nothing is invented."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=COMPANY_MAX)
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    status: ApplicationStatus = "applied"
    applied_on: date | None = None  # "yesterday" resolved against January's day
    channel: Channel | None = None
    contact_name: str | None = Field(default=None, max_length=CONTACT_MAX)
    contact_role: str | None = Field(default=None, max_length=CONTACT_MAX)
    notes: str | None = Field(default=None, max_length=NOTES_MAX)

    @model_validator(mode="after")
    def _planned_has_no_date(self) -> "IntakeDraft":
        """A "to apply" application has no sending day yet."""
        if self.status == "to_apply":
            self.applied_on = None
        return self

    @field_validator(
        "applied_on", "channel", "contact_name", "contact_role", "notes", mode="before"
    )
    @classmethod
    def _blank_is_absent(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value


@dataclass(frozen=True)
class IntakeContext:
    """January's day (her time zone) and the language of her interface."""

    today: date
    language: str


@dataclass(frozen=True)
class AlertView:
    """An existing application similar to the one being drafted: its strength, its id and the
    message (date and status, SPEC 6.3)."""

    level: AlertStrength
    application_id: str
    message: str


@dataclass(frozen=True)
class InfoView:
    """A "same company" notice: the close application and the message."""

    application_id: str
    company: str
    title: str
    status: ApplicationStatus
    message: str


class ApplicationStore(Protocol):
    async def intake_context(self, user_id: str) -> IntakeContext:
        """January's day (time zone from her settings) and the language of her interface."""
        ...

    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]:
        """The applications that block creation (see the module), strongest first."""
        ...

    async def intake_info(self, user_id: str, draft: IntakeDraft) -> list[InfoView]:
        """The plain notices (same company within 30 days), most recent first."""
        ...

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        """Creates the application and returns its id; idempotent per session. `distinct_from`:
        the alerted applications January confirmed as "another position"; 409
        `application_duplicate` if a similar application is not covered."""
        ...


def applications_unavailable() -> AppError:
    return AppError("applications_unavailable", "Applications are not wired to this engine.", 503)


class _NoApplications:
    """Engine default (tests, startups without the feature)."""

    async def intake_context(self, user_id: str) -> IntakeContext:
        raise applications_unavailable()

    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]:
        raise applications_unavailable()

    async def intake_info(self, user_id: str, draft: IntakeDraft) -> list[InfoView]:
        raise applications_unavailable()

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        raise applications_unavailable()


NO_APPLICATIONS: ApplicationStore = _NoApplications()
