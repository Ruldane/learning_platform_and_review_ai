from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.db.models.podcast import PodcastEpisode
from app.db.repository import UserScopedRepository


class EpisodeRepository(UserScopedRepository[PodcastEpisode]):
    model = PodcastEpisode

    async def by_day(self, day: date) -> PodcastEpisode | None:
        stmt = select(PodcastEpisode).where(
            PodcastEpisode.user_id == self.user_id, PodcastEpisode.day == day
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def reserve(
        self, day: date, lesson_id: str, module_id: str, title: str
    ) -> PodcastEpisode:
        stmt = (
            insert(PodcastEpisode)
            .values(
                user_id=self.user_id,
                day=day,
                lesson_id=lesson_id,
                module_id=module_id,
                title=title[:240],
                status="queued",
            )
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
        )
        await self.session.execute(stmt)
        row = await self.by_day(day)
        if row is None:
            raise RuntimeError("L’épisode réservé est introuvable.")
        return row
