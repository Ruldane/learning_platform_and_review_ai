"""Contract of the daily brief (SPEC 14.2, P11, P12, D162). A snapshot: the sections computed by
the code (block, reviews, reminders, offers, week) are frozen at creation; the resource and the
advice arrive later, written by the agents. Each section leads to the live screen."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.models.applications import ReminderKind
from app.db.models.daily import AdviceStatus, BriefOrigin


class BriefBlockTask(BaseModel):
    title: str
    minutes: int


class BlockRubric(BaseModel):
    """The study block of the day: the lesson and its due tasks (`minutes`: their total)."""

    module_title: str
    lesson_id: str
    lesson_title: str
    minutes: int
    tasks: list[BriefBlockTask]


class ReviewsRubric(BaseModel):
    """`queue`: the cards in today's queue; `remaining`: those due beyond the queue."""

    queue: int
    remaining: int


class ReminderItem(BaseModel):
    reminder_id: str
    application_id: str
    company: str
    title: str
    kind: ReminderKind
    due_on: date


class RemindersRubric(BaseModel):
    """`due`: all due reminders; `items`: the first 5."""

    due: int
    items: list[ReminderItem]


class OfferItem(BaseModel):
    url: str
    title: str | None
    company: str | None
    score: int
    run_id: str | None = None
    offer_ref: str | None = None


class OffersRubric(BaseModel):
    """New radar offers (score at least 70), 5 at most; `run_id`: the run of the best one
    (`None` without an offer)."""

    run_id: str | None
    items: list[OfferItem]


class WeekRubric(BaseModel):
    """Progress of the local week of the most recent validated program."""

    planned_minutes: int
    done_minutes: int
    tasks_done: int
    tasks_total: int
    study_minutes: int
    streak_days: int


class BriefResourceOut(BaseModel):
    """The resource of the day: a real web result whose page was read. `published`: its date if
    the web gives it, never guessed."""

    title: str
    url: str
    domain: str
    published: str | None
    why: str


class BriefOut(BaseModel):
    """The brief of a local day. `advice_status`: `pending` while the advice session lives (the
    only state that still changes); `ready` (`advice` stored); `failed` (advice impossible or
    session dead) and `unavailable` (no model) are **final for the day**: the advice is never
    relaunched, there is no "Retry" to offer."""

    id: str
    day: date
    origin: BriefOrigin
    generated_at: datetime
    block: BlockRubric | None
    reviews: ReviewsRubric
    reminders: RemindersRubric
    offers: OffersRubric
    reading_unread: int = 0
    week: WeekRubric | None
    resource: BriefResourceOut | None
    unavailable: list[str] = Field(
        default_factory=list,
        description="Sections whose source was down at creation (empty for that day).",
    )
    advice: list[str] | None
    advice_status: AdviceStatus = Field(
        description="`pending` may still change; `ready`, `failed` and `unavailable` are final."
    )
    session_id: str | None
