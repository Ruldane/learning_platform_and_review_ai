"""The cards are those of the real queue, the learned skills those of the reference data."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.features.quiz.service.cards import due_queue
from app.features.quiz.service.runtime import QuizRuntime
from app.features.skills.service import SkillsService
from app.features.study_return import repository
from app.features.study_return.schemas import (
    StudyReturnCard,
    StudyReturnLastBlock,
    StudyReturnSelection,
    StudyReturnSkill,
)

CARDS_MAX = 3
SKILLS_MAX = 2


async def _skills(
    db: AsyncSession, user_id: str, cards: list[StudyReturnCard]
) -> list[StudyReturnSkill]:
    service = SkillsService(db, user_id)
    priority = {normalize_skill_name(card.skill) for card in cards if card.skill}
    catalog = await service.catalog()
    catalog.sort(key=lambda item: normalize_skill_name(item[0]) not in priority)
    acquired = []
    for name, level in catalog:
        if level not in ("validated", "proven"):
            continue
        skill_id = await service.skill_id_for(name)
        if skill_id is not None:
            acquired.append(StudyReturnSkill(id=skill_id, name=name, level=level))
        if len(acquired) >= SKILLS_MAX:
            break
    return acquired


async def _last_block(db: AsyncSession, user_id: str) -> StudyReturnLastBlock | None:
    found = await repository.last_finished(db, user_id)
    if found is None:
        return None
    row, title = found
    if row.ended_at is None:
        return None
    return StudyReturnLastBlock(
        id=row.id,
        kind="training" if row.kind == "training" else "guided",
        title=title,
        minutes=row.minutes,
        ended_at=row.ended_at,
    )


async def choose(db: AsyncSession, user_id: str, quiz: QuizRuntime) -> StudyReturnSelection:
    queue = await due_queue(quiz, db, user_id)
    cards = [
        StudyReturnCard(id=card.id, front=card.front, skill=card.skill, due_date=card.due_date)
        for card in queue.cards[:CARDS_MAX]
        if card.due_date is not None
    ]
    skills = await _skills(db, user_id, cards)
    last = await _last_block(db, user_id)
    minutes = 2 * len(cards) + (3 if skills else 0) + (3 if last else 0)
    return StudyReturnSelection(minutes=minutes or 5, skills=skills, cards=cards, last_block=last)
