"""The brief sections computed by the code (P11, D162): study block, reviews, reminders, new radar
offers, week progress. No model here: each section is a fact read from another feature (its
service), frozen as JSON in the daily brief.

A section with nothing to show is `None` (no block planned, no validated program); the counts
(`reviews`, `reminders`) are 0. `offers.items[*].key` (the normalised link) and `week.best_quiz`
are internal brief details, never returned by the API: the first feeds "already shown" for the
next 7 days, the second the advice facts. Each section is computed separately (savepoint): a
failing source empties its section and names it in `unavailable`, never a 500 error for the
whole morning screen (D173). Logs: the section name and the exception class."""

import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment, user_zone, week_start
from app.features.applications.service.reminders import list_reminders
from app.features.brief.repository import BriefRepository
from app.features.brief.schemas import (
    BlockRubric,
    BriefBlockTask,
    OfferItem,
    OffersRubric,
    ReminderItem,
    RemindersRubric,
    ReviewsRubric,
    WeekRubric,
)
from app.features.brief.service.rules import REMINDERS_MAX, SHOWN_BRIEFS, new_offers
from app.features.brief.service.runtime import BriefRuntime
from app.features.program.service.programs import list_programs
from app.features.quiz.service.cards import due_queue
from app.features.radar.service.views import offers_since
from app.features.replan.service.facts import week_facts
from app.features.settings.service import SettingsService
from app.features.study.service.block import block_of_day
from app.features.study.service.view import summary


async def _block(db: AsyncSession, user_id: str, today: date) -> dict[str, Any] | None:
    block = await block_of_day(db, user_id, today)
    if block is None:
        return None
    return BlockRubric(
        module_title=block.module_title,
        lesson_id=block.lesson_id,
        lesson_title=block.lesson_title,
        minutes=sum(task.minutes for task in block.tasks),
        tasks=[BriefBlockTask(title=task.title, minutes=task.minutes) for task in block.tasks],
    ).model_dump(mode="json")


async def _reviews(rt: BriefRuntime, db: AsyncSession, user_id: str) -> dict[str, Any]:
    queue = await due_queue(rt.quiz, db, user_id)
    return ReviewsRubric(queue=len(queue.cards), remaining=queue.remaining_due).model_dump()


async def _reminders(rt: BriefRuntime, user_id: str) -> dict[str, Any]:
    due = await list_reminders(rt.applications, user_id, due=True)
    return RemindersRubric(
        due=len(due),
        items=[
            ReminderItem(
                reminder_id=item.id,
                application_id=item.application_id,
                company=item.company,
                title=item.title,
                kind=item.kind,
                due_on=item.due_on,
            )
            for item in due[:REMINDERS_MAX]
        ],
    ).model_dump(mode="json")


async def _offers(db: AsyncSession, user_id: str, today: date, now: datetime) -> dict[str, Any]:
    """Re-rank the local week and publish the new entries among its five best offers."""
    repo = BriefRepository(db, user_id)
    monday = week_start(today)
    settings = await SettingsService(db, user_id).get()
    start = local_moment(monday, "00:00", user_zone(settings.timezone))
    postings = await offers_since(db, user_id, start, until=now)
    earlier = await repo.before(today, SHOWN_BRIEFS)
    shown = {str(key) for brief in earlier for key in brief.offer_keys}
    this_week = {str(key) for brief in earlier if brief.day >= monday for key in brief.offer_keys}
    ranked = new_offers(postings, shown - this_week, await repo.known_keys())
    chosen = [posting for posting in ranked if posting["url_key"] not in shown]
    rubric = OffersRubric(
        run_id=str(chosen[0]["run_id"]) if chosen else None,
        items=[
            OfferItem(
                url=str(posting["url"]),
                title=posting.get("title"),
                company=posting.get("company"),
                score=posting["score"],
                run_id=posting["run_id"],
                offer_ref=posting["offer_ref"],
            )
            for posting in chosen
        ],
    ).model_dump()
    for item, posting in zip(rubric["items"], chosen, strict=True):
        item["key"] = posting["url_key"]
    return rubric


async def _week(
    rt: BriefRuntime, db: AsyncSession, user_id: str, today: date
) -> dict[str, Any] | None:
    """The local week of the most recent validated program; the streak comes from
    the study summary."""
    programs = await list_programs(db, user_id)
    current = next((program for program in programs if program.status == "validated"), None)
    if current is None:
        return None
    facts = await week_facts(db, user_id, current.id, week_start(today))
    rubric = WeekRubric(
        planned_minutes=facts.planned_minutes,
        done_minutes=facts.done_minutes,
        tasks_done=facts.tasks_done,
        tasks_total=facts.tasks_planned,
        study_minutes=facts.study_minutes,
        streak_days=(await summary(rt.study, db, user_id)).streak_days,
    ).model_dump()
    rubric["best_quiz"] = max(facts.quiz_scores) if facts.quiz_scores else None
    return rubric


logger = logging.getLogger(__name__)


def _empty(name: str) -> Any:
    """The value of a section whose source is down: empty, never made up. A fresh value on each
    call (never a shared object); the front end and the advice read `unavailable`."""
    empty: dict[str, Any] = {
        "block": None,
        "reviews": {"queue": 0, "remaining": 0},
        "reminders": {"due": 0, "items": []},
        "offers": {"run_id": None, "items": []},
        "week": None,
    }
    return empty[name]


async def _isolated(
    db: AsyncSession, name: str, build: Callable[[], Awaitable[Any]], failed: list[str]
) -> Any:
    """Section `name`, in its own savepoint: on failure, its empty value and its name in `failed`
    (the transaction stays valid for the following sections). `build` is a factory: the
    coroutine only exists once the savepoint is open, never abandoned."""
    try:
        async with db.begin_nested():
            return await build()
    except Exception as exc:
        logger.warning("Brief: section %s unavailable (%s)", name, type(exc).__name__)
        failed.append(name)
        return _empty(name)


async def build_sections(
    rt: BriefRuntime, db: AsyncSession, user_id: str, today: date
) -> dict[str, Any]:
    """The code sections (`BRIEF_KEYS`) of the local day `today`, plus `unavailable` (the
    failing sections) only if there are any."""
    failed: list[str] = []
    sections: dict[str, Any] = {
        "block": await _isolated(db, "block", lambda: _block(db, user_id, today), failed),
        "reviews": await _isolated(db, "reviews", lambda: _reviews(rt, db, user_id), failed),
        "reminders": await _isolated(db, "reminders", lambda: _reminders(rt, user_id), failed),
        "offers": await _isolated(
            db, "offers", lambda: _offers(db, user_id, today, rt.now()), failed
        ),
        "week": await _isolated(db, "week", lambda: _week(rt, db, user_id, today), failed),
    }
    if failed:
        sections["unavailable"] = failed
    return sections
