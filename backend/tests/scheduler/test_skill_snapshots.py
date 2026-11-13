"""Tâche « relevés des compétences » (D106, F20) : un relevé par utilisateur et par semaine
locale (le premier passage l'écrit, les suivants ne changent rien) ; la semaine change au minuit
du lundi chez January, pas à minuit UTC."""

from datetime import UTC, date, datetime

from sqlalchemy import select

from app.db.models.skills import Skill, SkillSnapshot, UserSkill
from app.features.skills.service import write_weekly_snapshots
from tests.features.program.support import Factory

ME, OTHER = "moi", "autre"


async def _level(factory: Factory, user_id: str, name: str, level: str) -> str:
    async with factory() as db:
        skill = Skill(user_id=user_id, name=name, norm_name=name, domain="Données")
        db.add(skill)
        await db.flush()
        db.add(UserSkill(user_id=user_id, skill_id=skill.id, level=level))
        await db.commit()
        return skill.id


async def _snapshots(factory: Factory) -> list[tuple[str, date, dict[str, str]]]:
    async with factory() as db:
        rows = await db.execute(select(SkillSnapshot).order_by(SkillSnapshot.week_start))
        return [(r.user_id, r.week_start, dict(r.levels)) for r in rows.scalars()]


async def test_skill_snapshot_once_per_local_week(db_session_factory: Factory) -> None:
    pandas = await _level(db_session_factory, ME, "pandas", "en_cours")
    await _level(db_session_factory, OTHER, "sql", "valide")
    sunday = datetime(2026, 11, 22, 22, 59, tzinfo=UTC)  # dimanche 23:59 à Paris
    assert await write_weekly_snapshots(db_session_factory, sunday) == 2
    async with db_session_factory() as db:
        row = (await db.execute(select(UserSkill).where(UserSkill.user_id == ME))).scalar_one()
        row.level = "valide"
        await db.commit()
    assert await write_weekly_snapshots(db_session_factory, sunday) == 0  # le premier gagne
    monday = datetime(2026, 11, 22, 23, 1, tzinfo=UTC)  # lundi 00:01 à Paris, dimanche en UTC
    assert await write_weekly_snapshots(db_session_factory, monday) == 2
    mine = [(week, levels) for user, week, levels in await _snapshots(db_session_factory)
            if user == ME]  # fmt: skip
    assert mine == [
        (date(2026, 11, 16), {pandas: "en_cours"}),
        (date(2026, 11, 23), {pandas: "valide"}),
    ]
