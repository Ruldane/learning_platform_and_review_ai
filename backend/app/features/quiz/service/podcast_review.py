from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment
from app.features.quiz.repository import FlashcardRepository


async def yesterday_errors(
    db: AsyncSession, user_id: str, day: date, zone: ZoneInfo
) -> tuple[str, ...]:
    start = local_moment(day - timedelta(days=1), "00:00", zone)
    end = local_moment(day, "00:00", zone)
    cards = await FlashcardRepository(db, user_id).recent_quiz_errors(start, end)
    return tuple(f"{front[:500]}\n{back[:500]}" for front, back in cards)
