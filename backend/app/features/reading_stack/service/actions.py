"""Explicit actions on a reading reuse the owning services."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.db.models.reading_stack import ReadingItem
from app.features.applications.service.create import ApplicationIn, create_application
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.memory.service.direct import author_of, write_direct
from app.features.memory.service.runtime import MemoryRuntime
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.reading_stack.schemas import ReadingApplicationIn
from app.features.replan.service.launch import start_reading_replan
from app.features.replan.service.runtime import ReplanRuntime
from app.features.settings.service import SettingsService
from app.mcp.recorder import ACTIVE


@dataclass(frozen=True)
class ReadingActions:
    memory: MemoryRuntime
    replan: ReplanRuntime
    applications: ApplicationsRuntime


async def keep_memory(actions: ReadingActions, db: AsyncSession, row: ReadingItem) -> str:
    text = f"{row.text or row.summary}\n\n[Source]({row.url})"
    return await write_direct(
        db,
        actions.memory,
        row.user_id,
        kind="document",
        title=row.title,
        text=text,
        tags=["reading stack"],
        author=author_of(ACTIVE.get() is not None),
        reason="Reading kept in memory.",
    )


def _passage_front(row: ReadingItem, passage: str) -> str:
    cue = " ".join(passage.split()[:6])
    return f"What should you remember from the passage “{cue}…” in “{row.title}”?"


async def make_card(db: AsyncSession, row: ReadingItem, *, passage: str | None = None) -> int:
    normalized = (row.text or "").replace("\r\n", "\n").replace("\r", "\n")
    if passage is not None and passage not in normalized:
        raise AppError("reading_passage_missing", "This passage is no longer in the reading.", 409)
    content = passage or (row.summary.strip() or row.text.strip())[:1650]
    if not content:
        raise AppError("reading_content_missing", "This reading has no summary.", 409)
    settings = await SettingsService(db, row.user_id).get()
    card = NewCard(
        front=_passage_front(row, passage)
        if passage
        else f"What should you remember from “{row.title}”?",
        back=f"{content}\n\n{row.url}",
        skill=None,
        module_id=None,
        source="capture",
        source_id=row.id,
    )
    return await add_cards(db, row.user_id, [card], local_today(user_zone(settings.timezone)))


async def propose_reading(actions: ReadingActions, row: ReadingItem, program_id: str) -> str:
    return await start_reading_replan(actions.replan, row.user_id, program_id, row.title, row.url)


async def keep_offer(actions: ReadingActions, row: ReadingItem, body: ReadingApplicationIn) -> str:
    if row.kind != "offer":
        raise AppError(
            "reading_offer_required", "Choose a job posting from the reading stack.", 409
        )
    created = await create_application(
        actions.applications,
        row.user_id,
        ApplicationIn(
            company=body.company,
            title=row.title[:200],
            url=row.url,
            posting_text=row.text or None,
            distinct_from=body.distinct_from,
        ),
    )
    return created.application.id
