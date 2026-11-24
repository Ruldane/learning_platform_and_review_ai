"""Spaced-review cards (SPEC F9, D101): creation deduplicated by front, today's queue
(30 cards at most, 15 minutes) and reviews. Days are January's (time zone, D98).

A review is guarded by the due date (`due_date ≤ local today`): the second of two simultaneous
reviews finds the card already pushed back (409 `card_not_due`). Two failures in a row on the
cards of a `valide` skill bring it back down to `en_cours` (`record_review`); memory reflects
it after the commit (`allow_lower`, the only decrease allowed). Logs: identifiers only, never
the front or the back."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.study_schema import card_hash
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.study import CardSource, Flashcard
from app.features.memory.service.skill_levels import reflect_skill_level
from app.features.quiz.repository import FlashcardRepository
from app.features.quiz.schemas import DueQueue, FlashcardOut, ReviewOut
from app.features.quiz.service.runtime import QuizRuntime
from app.features.quiz.service.spacing import DAILY_CARDS, first_due, next_review, queue_room
from app.features.skills.service import SkillsService

logger = logging.getLogger(__name__)

FRONT_MAX = 2000
BACK_MAX = 2000
SKILL_MAX = 120


@dataclass(frozen=True)
class NewCard:
    front: str
    back: str
    skill: str | None
    module_id: str | None
    source: CardSource
    source_id: str | None


async def add_cards(db: AsyncSession, user_id: str, cards: Iterable[NewCard], today: date) -> int:
    """Writes the cards whose front is new (due tomorrow); returns the number created."""
    repo = FlashcardRepository(db, user_id)
    created = 0
    for card in cards:
        front = card.front.strip()[:FRONT_MAX]
        if not front:
            continue
        created += await repo.insert_once(
            front=front,
            back=card.back.strip()[:BACK_MAX],
            front_hash=card_hash(front),
            skill=card.skill[:SKILL_MAX] if card.skill else None,
            module_id=card.module_id,
            source=card.source,
            source_id=card.source_id,
            step=0,
            due_date=first_due(today),
        )
    return created


async def due_queue(rt: QuizRuntime, db: AsyncSession, user_id: str) -> DueQueue:
    """Today's queue: due cards, most overdue first, within the room left."""
    today = await rt.today(db, user_id)
    repo = FlashcardRepository(db, user_id)
    reviewed = await repo.count_reviewed(today)
    cards = await repo.due(today, queue_room(reviewed))
    total = await repo.count_due(today)
    return DueQueue(
        cards=[
            FlashcardOut(id=c.id, front=c.front, back=c.back, skill=c.skill, due_date=c.due_date)
            for c in cards
        ],
        reviewed_today=reviewed,
        daily_cards=DAILY_CARDS,
        remaining_due=max(0, total - len(cards)),
    )


async def due_skill_names(db: AsyncSession, user_id: str, today: date) -> set[str]:
    """Normalized names of the skills that have a due card (≤ `today`, January's day): the
    map's "Review" next action (D107). Read for the other features."""
    skills = await FlashcardRepository(db, user_id).due_skills(today)
    return {norm for norm in map(normalize_skill_name, skills) if norm}


async def count_due_cards(db: AsyncSession, user_id: str, today: date) -> int:
    return await FlashcardRepository(db, user_id).count_due(today)


def card_not_found() -> AppError:
    return AppError("card_not_found", "Card not found.", 404)


def card_not_due() -> AppError:
    return AppError("card_not_due", "This card is not due for review today.", 409)


async def _due_card(repo: FlashcardRepository, card_id: str, today: date) -> Flashcard:
    card = await repo.get_fresh(card_id)
    if card is None:
        raise card_not_found()
    if card.due_date > today:
        raise card_not_due()
    return card


async def read_due_card(
    rt: QuizRuntime, db: AsyncSession, user_id: str, card_id: str
) -> FlashcardOut:
    card = await _due_card(FlashcardRepository(db, user_id), card_id, await rt.today(db, user_id))
    return FlashcardOut(
        id=card.id, front=card.front, back=card.back, skill=card.skill, due_date=card.due_date
    )


async def review_in_session(
    rt: QuizRuntime,
    db: AsyncSession,
    user_id: str,
    card_id: str,
    ok: bool,
    *,
    expected_due: date | None = None,
) -> ReviewOut:
    """Applies the same review in the transaction that commits a channel's answer."""
    today = await rt.today(db, user_id)
    repo = FlashcardRepository(db, user_id)
    card = await _due_card(repo, card_id, today)
    if expected_due is not None and card.due_date != expected_due:
        raise card_not_due()
    step, due = next_review(card.step, ok, today)
    if not await repo.claim_review(card, today, step, due):
        raise card_not_due()
    demoted: str | None = None
    if card.skill:
        skills = SkillsService(db, user_id)
        if await skills.record_review(card.skill, ok) is not None:
            demoted = await skills.display_name(card.skill)
    return ReviewOut(card_id=card_id, step=step, due_date=due, demoted_skill=demoted)


async def review_card(rt: QuizRuntime, user_id: str, card_id: str, ok: bool) -> ReviewOut:
    """Review of a due card: step and due date updated (a failure: local tomorrow)."""
    async with rt.session_factory() as db:
        out = await review_in_session(rt, db, user_id, card_id, ok)
        await db.commit()
    await reflect_review(rt, user_id, out)
    return out


async def reflect_review(rt: QuizRuntime, user_id: str, out: ReviewOut) -> None:
    """Reflects in memory a level change whose transaction is committed."""
    demoted = out.demoted_skill
    if demoted is not None:
        try:
            await reflect_skill_level(
                rt.memory,
                user_id,
                title=demoted,
                level="en_cours",
                author="user",
                session_id=None,
                reason="Two failures in a row on the review cards",
                allow_lower=True,
            )
        except Exception:
            logger.warning("Demotion not reflected: user %s, card %s", user_id, out.card_id)
        logger.info("Skill demoted: user %s, card %s", user_id, out.card_id)
