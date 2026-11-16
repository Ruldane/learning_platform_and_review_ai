"""Matériel des tests du fil d'activité (8.7) : des lignes posées directement dans les tables que
lisent les sources, à des instants connus. Aucun agent, aucun réseau."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import User
from app.db.models.daily import Brief, JobRun, RadarRun
from app.db.models.lessons import Lesson
from app.db.models.memory import MemoryWrite
from app.features.activity.schemas import ActivityPage
from app.features.activity.service.feed import activity_page

API = "/api/v1/activity"
T0 = datetime(2026, 11, 17, 6, 0, tzinfo=UTC)
OTHER = "autre-utilisatrice"
Factory = async_sessionmaker[AsyncSession]


def hours(count: float) -> datetime:
    return T0 + timedelta(hours=count)


def minutes(count: int) -> datetime:
    return T0 + timedelta(minutes=count)


@dataclass
class Env:
    app: FastAPI
    user_id: str

    @property
    def factory(self) -> Factory:
        factory: Factory = self.app.state.session_factory
        return factory


async def add_user(env: Env, user_id: str = OTHER) -> None:
    async with env.factory() as db:
        db.add(User(id=user_id, user_id=user_id))
        await db.commit()


async def set_lesson(env: Env, lesson_id: str, status: str, at: datetime) -> None:
    """La leçon (posée par `seed`) dans l'état `status`, dernier changement à `at`."""
    async with env.factory() as db:
        await db.execute(
            update(Lesson).where(Lesson.id == lesson_id).values(status=status, updated_at=at)
        )
        await db.commit()


async def add_run(env: Env, at: datetime, *, user: str | None = None, **over: object) -> str:
    fields: dict[str, object] = {
        "user_id": user or env.user_id,
        "role": "Poste secret",
        "zone": "Zone secrète",
        "role_norm": "poste secret",
        "zone_norm": "zone secrete",
        "trigger": "manual",
        "status": "done",
        "read_count": 47,
        "blocked_count": 6,
        "finished_at": at,
    }
    async with env.factory() as db:
        row = RadarRun(**(fields | over))
        db.add(row)
        await db.commit()
        return row.id


async def add_brief(
    env: Env, at: datetime, *, user: str | None = None, day: str = "2026-11-17"
) -> str:
    async with env.factory() as db:
        row = Brief(
            user_id=user or env.user_id,
            day=datetime.fromisoformat(day).date(),
            origin="opening",
            created_at=at,
        )
        db.add(row)
        await db.commit()
        return row.id


async def add_write(
    env: Env,
    at: datetime,
    *,
    author: str = "archivist",
    action: str = "create",
    title: str = "Élément secret",
    reason: str | None = "Raison secrète.",
    user: str | None = None,
) -> str:
    async with env.factory() as db:
        row = MemoryWrite(
            user_id=user or env.user_id,
            item_id="item-1",
            item_title=title,
            kind="acquis",
            action=action,
            author=author,
            reason=reason,
            created_at=at,
        )
        db.add(row)
        await db.commit()
        return row.id


async def add_job(
    env: Env,
    at: datetime,
    *,
    name: str = "daily_brief",
    period: str = "2026-11-17",
    code: str | None = "engine_unavailable",
    status: str = "failed",
    attempts: int = 1,
    user: str | None = None,
) -> str:
    async with env.factory() as db:
        row = JobRun(
            user_id=user or env.user_id,
            name=name,
            period=period,
            status=status,
            started_at=at - timedelta(minutes=1),
            finished_at=at,
            attempts=attempts,
            error_code=code,
        )
        db.add(row)
        await db.commit()
        return row.id


async def page(
    env: Env,
    user: str | None = None,
    *,
    after: datetime | None = None,
    before: datetime | None = None,
    after_id: str | None = None,
    before_id: str | None = None,
    limit: int = 30,
) -> ActivityPage:
    async with env.factory() as db:
        return await activity_page(
            db,
            user or env.user_id,
            after=after,
            before=before,
            after_id=after_id,
            before_id=before_id,
            limit=limit,
        )
