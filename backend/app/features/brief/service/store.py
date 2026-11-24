"""Port of the `daily_brief` flow (`BriefStore`, D161) on the `brief` feature: implementation wired
by `bootstrap_agents.agent_ports(..., brief=...)`. Each call opens its own short database
session.

`context` re-reads the brief: the advice facts come from the code sections (never recounted
here), the resource topic is "{target field} news" (`service.topic`: radar role, goal role, a
topic taken from the goal text, validated program title; none: `None`, no search), the numbers
allowed in the advice are those of the facts (`advice_numbers`, as digits).
Writes are **conditional and idempotent** (SPEC 9.4): the resource is written only if still
absent (`WHERE resource IS NULL`), the advice only if still `pending`; the first write wins,
including a `None` advice (`failed` or `unavailable`), which therefore stays so all day. Logs:
ids and numbers; never a fact, a topic, a resource or a sentence (17.2)."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any, Literal

from app.agents.tools.brief_port import AdviceFacts, BriefContext
from app.agents.tools.brief_schema import ResourceView
from app.features.brief.repository import BriefRepository
from app.features.brief.service.rules import advice_numbers
from app.features.brief.service.runtime import BriefRuntime
from app.features.brief.service.topic import resource_topic
from app.features.brief.service.views import brief_not_found
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)


def facts_of(sections: dict[str, Any]) -> AdviceFacts:
    """The day's facts as the brief sections state them: the block, the queued cards, the due
    reminders, the offers shown, the week (no program: zeros). The fact of a failing section
    (`unavailable`) is `None`: never a made-up zero for the advice."""
    down = frozenset(sections.get("unavailable", ()))
    block: dict[str, Any] | None = sections.get("block")
    week: dict[str, Any] = sections.get("week") or {}

    def known(name: str, value: int) -> int | None:
        return None if name in down else value

    return AdviceFacts(
        block_title=block["lesson_title"] if block else None,
        block_minutes=known("block", block["minutes"] if block else 0),
        cards_due=known("reviews", sections["reviews"]["queue"]),
        reminders_due=known("reminders", sections["reminders"]["due"]),
        offers=known("offers", len(sections["offers"]["items"])),
        best_score=week.get("best_quiz"),
        week_planned=known("week", week.get("tasks_total", 0)),
        week_done=known("week", week.get("tasks_done", 0)),
        streak_days=known("week", week.get("streak_days", 0)),
    )


def allowed_numbers(facts: AdviceFacts) -> frozenset[str]:
    """Numbers the advice may quote: those of the facts, as digits only."""
    return frozenset(
        advice_numbers(
            {
                "minutes": facts.block_minutes,
                "cards": facts.cards_due,
                "reminders": facts.reminders_due,
                "offers": facts.offers,
                "score": facts.best_score,
                "planned": facts.week_planned,
                "done": facts.week_done,
                "streak": facts.streak_days,
            }
        )
    )


class AgentBriefStore:
    def __init__(self, runtime: BriefRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, brief_id: str) -> BriefContext:
        async with self._rt.session_factory() as db:
            row = await BriefRepository(db, user_id).get_fresh(brief_id)
            if row is None:
                raise brief_not_found()
            settings = await SettingsService(db, user_id).get()
            topic = await resource_topic(db, user_id)
        facts = facts_of(row.sections)
        language: Literal["fr", "en"] = "en" if settings.lesson_language == "en" else "fr"
        return BriefContext(
            brief_id=row.id,
            day=row.day,
            language=language,
            topic=topic,
            facts=facts,
            resource_done=row.resource is not None,
            advice_done=row.advice_status != "pending",
            allowed_numbers=allowed_numbers(facts),
        )

    async def _written(
        self, user_id: str, brief_id: str, write: Callable[[BriefRepository], Awaitable[bool]]
    ) -> bool:
        """Apply the write `write(repo)`; 404 if the brief does not belong to this user."""
        async with self._rt.session_factory() as db:
            repo = BriefRepository(db, user_id)
            written = await write(repo)
            await db.commit()
            if not written and await repo.get(brief_id) is None:
                raise brief_not_found()
        return written

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None:
        data: dict[str, Any] = asdict(resource) if resource is not None else {}
        written = await self._written(user_id, brief_id, lambda r: r.save_resource(brief_id, data))
        logger.info(
            "Resource stored: session %s, brief %s, first write %s, empty %s",
            session_id,
            brief_id,
            written,
            resource is None,
        )

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None:
        if sentences is not None:
            sentences_data = {"sentences": list(sentences)}
            written = await self._written(
                user_id, brief_id, lambda r: r.save_advice(brief_id, sentences_data)
            )
        else:
            status = "unavailable" if unavailable else "failed"
            written = await self._written(
                user_id, brief_id, lambda r: r.close_advice(brief_id, status)
            )
        logger.info(
            "Advice stored: session %s, brief %s, first write %s, written %s",
            session_id,
            brief_id,
            written,
            sentences is not None,
        )
