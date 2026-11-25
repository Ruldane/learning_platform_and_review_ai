"""Applications schemas (SPEC 6, D139). A 422 names the fields (`details.fields`), never their
value: company, job title, contacts and notes are personal data. A duplicate 409 returns the
existing records (`AlertOut`), never the input."""

from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.db.models.applications import ApplicationStatus as ApplicationStatus
from app.db.models.applications import Channel, EventKind, ReminderKind
from app.db.models.applications import ReminderStatus as ReminderState

COMPANY_MAX = 200
TITLE_MAX = 200
URL_MAX = 2000
POSTING_TEXT_MAX = 60_000
TEXT_MAX = 2000  # a timeline note
NOTES_MAX = 10_000
LETTER_MAX = 20_000
CONTACTS_MAX = 10
DISTINCT_MAX = 50

AlertLevel = Literal["certain", "probable", "possible", "info"]


def _link(value: str) -> str:
    """An `http` or `https` link with a host; the value is never quoted in the error."""
    try:
        parts = urlsplit(value)
        ok = parts.scheme.lower() in ("http", "https") and bool(parts.hostname)
    except ValueError:
        ok = False
    if not ok:
        raise ValueError("invalid link")
    return value


def _text(max_length: int) -> StringConstraints:
    return StringConstraints(strip_whitespace=True, max_length=max_length)


Company = Annotated[str, _text(COMPANY_MAX)]
Title = Annotated[str, _text(TITLE_MAX)]
Link = Annotated[str, _text(URL_MAX), AfterValidator(_link)]
Notes = Annotated[str, _text(NOTES_MAX)]
Id = Annotated[str, Field(min_length=1, max_length=36)]


class ContactIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    role: Annotated[str, _text(120)] | None = None
    url: Annotated[str, _text(500), AfterValidator(_link)] | None = None


class ContactOut(BaseModel):
    id: str
    name: str
    role: str | None
    url: str | None


class ApplicationIn(BaseModel):
    """Manual creation or from a posting. With `posting_id`, the company, job title, link and
    frozen text come from the posting (the given fields are only used if the posting does not
    state them yet); without `posting_id`, `company` and `title` are required (422 `fields`).
    `distinct_from`: the alert's records that January confirmed as "another position"."""

    posting_id: Id | None = None
    company: Company | None = None
    title: Title | None = None
    url: Link | None = None
    posting_text: Annotated[str, _text(POSTING_TEXT_MAX)] | None = None
    channel: Channel | None = None
    status: ApplicationStatus = "to_apply"
    applied_on: date | None = None
    notes: Notes | None = None
    contacts: list[ContactIn] = Field(default_factory=list, max_length=CONTACTS_MAX)
    distinct_from: list[Id] = Field(default_factory=list, max_length=DISTINCT_MAX)


class IntakeIn(BaseModel):
    """January's sentence: "I applied yesterday at X for the Y position" (1 to 1,000 characters).
    A 422 names `text`, never quoting it."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class IntakeOut(BaseModel):
    """The Tracking Assistant session: the record being prepared arrives through its events
    (`interrupt.requested`, `kind` `application_confirm`)."""

    session_id: str


class ApplicationPatch(BaseModel):
    """The fields to change (those sent; `null` clears an optional field); `contacts` replaces
    the list. `posting_text`: the posting text of a record entered without it (it unlocks its
    kit); an empty text clears it. The status only changes through
    `POST /applications/{id}/events`: sending it here is a 422 (`fields: ["status"]`), like any
    unknown field."""

    model_config = ConfigDict(extra="forbid")

    company: Company | None = None
    title: Title | None = None
    url: Link | None = None
    posting_text: Annotated[str, _text(POSTING_TEXT_MAX)] | None = None
    channel: Channel | None = None
    applied_on: date | None = None
    interview_on: date | None = None
    letter: Annotated[str, _text(LETTER_MAX)] | None = None
    notes: Notes | None = None
    next_action: Annotated[str, _text(200)] | None = None
    next_action_on: date | None = None
    contacts: list[ContactIn] | None = Field(default=None, max_length=CONTACTS_MAX)


class EventIn(BaseModel):
    """A timeline event: a status change (`status` required) or a note (`text` required). `on`:
    the day of the event (default: today, in January's time zone; never later: 422 `on`);
    `interview_on`: the interview day, for the "Interview" status (default: `on`)."""

    kind: Literal["status", "note"]
    status: ApplicationStatus | None = None
    text: Annotated[str, _text(TEXT_MAX)] | None = None
    on: date | None = None
    interview_on: date | None = None


class EventOut(BaseModel):
    id: str
    kind: EventKind
    at: datetime
    status_from: ApplicationStatus | None
    status_to: ApplicationStatus | None
    text: str | None
    ref_id: str | None


ReminderChannel = Literal["linkedin", "email", "none"]
ReminderActionName = Literal["done", "postpone", "ignore"]


class ReminderOut(BaseModel):
    """A follow-up: whom to contact, a draft ready to copy (fixed template, no LLM), the channel.
    Without a contact: `linkedin_search_url`, the prefilled LinkedIn search (company and target
    position). `close_21`: `channel` "none", `draft` is the suggestion to close the record."""

    id: str
    application_id: str
    kind: ReminderKind
    due_on: date
    status: ReminderState
    company: str
    title: str
    contact: ContactOut | None
    linkedin_search_url: str | None
    channel: ReminderChannel
    draft: str


class ReminderPatch(BaseModel):
    """Done, Postpone 3 days or Ignore; any other value is a 422 without echo."""

    action: ReminderActionName


class AlertOut(BaseModel):
    """An existing record that looks like the incoming posting: level, record, message (date and
    status). `info`: plain information, blocks nothing."""

    level: AlertLevel
    application_id: str
    company: str
    title: str
    status: ApplicationStatus
    applied_on: date | None
    created_on: date
    message: str


class ApplicationRef(BaseModel):
    id: str
    company: str
    title: str
    status: ApplicationStatus
    applied_on: date | None


class ApplicationOut(BaseModel):
    id: str
    posting_id: str | None
    company: str
    title: str
    url: str | None
    channel: Channel | None
    status: ApplicationStatus
    applied_on: date | None
    interview_on: date | None
    cv_version_id: str | None
    cv_version_number: int | None
    next_action: str | None
    next_action_on: date | None
    due_reminders: int
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationOut):
    posting_text: str | None
    letter: str | None
    notes: str | None
    contacts: list[ContactOut]
    events: list[EventOut]  # chronological
    reminders: list[ReminderOut]


class CreatedOut(BaseModel):
    application: ApplicationDetail
    info: list[AlertOut]  # another record at the same company within 30 days


class CheckOut(BaseModel):
    """`own`: this posting's record, if any; `alerts`: certain, probable, possible; `info`: same
    company within 30 days."""

    own: ApplicationRef | None
    alerts: list[AlertOut]
    info: list[AlertOut]


class ApplicationStatsOut(BaseModel):
    """The indicators (SPEC 6.4); `StatsOut` is already the name of the memory statistics."""

    by_status: dict[ApplicationStatus, int]
    response_rate: float | None
    mean_response_days: float | None
    due_reminders: int
