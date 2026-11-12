"""`SkillsService` (D88) : référentiel dédoublonné par nom normalisé, niveaux jamais baissés."""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.db.models.skills import Skill, SkillEdge, UserSkill
from app.features.skills.service import SkillsService

Factory = async_sessionmaker[AsyncSession]
ME, OTHER = "moi", "autre"


async def _count(factory: Factory, model: type) -> int:
    async with factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def test_upsert_catalog_dedups_and_links(db_session_factory: Factory) -> None:
    skills = [
        SkillDraft(name="Pandas", domain="Données", synonyms=["pd"]),
        SkillDraft(name="pandas ", domain="Autre"),
        SkillDraft(name="NumPy", domain="Calcul"),
    ]
    edges = [
        EdgeDraft(before="numpy", after="Pandas"),
        EdgeDraft(before="numpy", after="inconnue"),
        EdgeDraft(before="pandas", after="Pandas"),
    ]
    async with db_session_factory() as db:
        ids = await SkillsService(db, ME).upsert_catalog(skills, edges)
        again = await SkillsService(db, ME).upsert_catalog(skills, edges)
        await db.commit()
    assert set(ids) == {"pandas", "numpy"} and ids == again
    assert await _count(db_session_factory, Skill) == 2
    assert await _count(db_session_factory, SkillEdge) == 1
    async with db_session_factory() as db:
        pandas = (await db.execute(select(Skill).where(Skill.norm_name == "pandas"))).scalar_one()
    assert (pandas.name, pandas.domain) == ("Pandas", "Données")


async def test_raise_levels_never_lowers_and_reports_changes(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, ME)
        first = await service.raise_levels(["Pandas", "SQL"], "valide", "Quiz")
        second = await service.raise_levels(["pandas", "sql", "Rust"], "en_cours", "Programme P")
        third = await service.raise_levels(["Rust"], "en_cours", "Programme P")
        known = await service.known_levels()
        await db.commit()
    assert first == [("Pandas", "valide"), ("SQL", "valide")]
    assert second == [("Rust", "en_cours")]
    assert third == []
    assert known == {"pandas": "valide", "sql": "valide", "rust": "en_cours"}
    async with db_session_factory() as db:
        rows = (await db.execute(select(UserSkill))).scalars().all()
    pandas = next(r for r in rows if r.level == "valide" and "Programme P" in r.evidence)
    assert pandas.evidence == ["Quiz", "Programme P"]


async def test_levels_are_per_user(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        await SkillsService(db, OTHER).raise_levels(["Pandas"], "prouve", "Projet")
        await db.commit()
    async with db_session_factory() as db:
        assert await SkillsService(db, ME).known_levels() == {}
        assert await SkillsService(db, ME).raise_levels(["Pandas"], "declare", "x") == [
            ("Pandas", "declare")
        ]
        await db.commit()
    assert await _count(db_session_factory, Skill) == 2


async def test_concurrent_raises_create_one_skill(db_session_factory: Factory) -> None:
    async def raise_once() -> None:
        async with db_session_factory() as db:
            await SkillsService(db, ME).raise_levels(["Pandas"], "en_cours", "P")
            await db.commit()

    await asyncio.gather(raise_once(), raise_once())
    assert await _count(db_session_factory, Skill) == 1
    assert await _count(db_session_factory, UserSkill) == 1


async def test_levels_of_reads_current_levels_once_per_name(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, ME)
        await service.raise_levels(["Pandas"], "valide", "Quiz")
        await service.upsert_catalog([SkillDraft(name="Polars", domain="Données")], [])
        levels = await service.levels_of(["pandas", "PANDAS", "Polars", "inconnue", ""])
    assert levels == [("Pandas", "valide")]  # « Polars » n'a pas de niveau
