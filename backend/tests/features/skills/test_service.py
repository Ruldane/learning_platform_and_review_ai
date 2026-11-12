"""`SkillsService` (D88) : référentiel dédoublonné par nom normalisé, niveaux jamais baissés."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.core.skills import Evidence, EvidenceKind, evidence
from app.db.models.skills import Skill, SkillEdge, UserSkill
from app.features.skills.service import SkillsService

Factory = async_sessionmaker[AsyncSession]
ME, OTHER = "moi", "autre"
NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)


def _ev(label: str, kind: EvidenceKind = "program", ref_id: str | None = "r1") -> Evidence:
    return evidence(kind, ref_id, label, NOW)


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
        first = await service.raise_levels(["Pandas", "SQL"], "valide", _ev("Quiz", "quiz", "q1"))
        second = await service.raise_levels(
            ["pandas", "sql", "Rust"], "en_cours", _ev("Programme P")
        )
        third = await service.raise_levels(["Rust"], "en_cours", _ev("Programme P"))
        known = await service.known_levels()
        await db.commit()
    assert first == [("Pandas", "valide"), ("SQL", "valide")]
    assert second == [("Rust", "en_cours")]
    assert third == []
    assert known == {"pandas": "valide", "sql": "valide", "rust": "en_cours"}
    async with db_session_factory() as db:
        rows = (await db.execute(select(UserSkill))).scalars().all()
    pandas = next(r for r in rows if r.level == "valide" and len(r.evidence) == 2)
    assert [(e["kind"], e["label"]) for e in pandas.evidence] == [
        ("quiz", "Quiz"),
        ("program", "Programme P"),
    ]
    assert pandas.fail_streak == 0


async def test_levels_are_per_user(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        await SkillsService(db, OTHER).raise_levels(["Pandas"], "prouve", _ev("Projet", "project"))
        await db.commit()
    async with db_session_factory() as db:
        assert await SkillsService(db, ME).known_levels() == {}
        assert await SkillsService(db, ME).raise_levels(["Pandas"], "declare", _ev("x")) == [
            ("Pandas", "declare")
        ]
        await db.commit()
    assert await _count(db_session_factory, Skill) == 2


async def test_concurrent_raises_create_one_skill(db_session_factory: Factory) -> None:
    async def raise_once() -> None:
        async with db_session_factory() as db:
            await SkillsService(db, ME).raise_levels(["Pandas"], "en_cours", _ev("P"))
            await db.commit()

    await asyncio.gather(raise_once(), raise_once())
    assert await _count(db_session_factory, Skill) == 1
    assert await _count(db_session_factory, UserSkill) == 1


async def test_levels_of_reads_current_levels_once_per_name(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, ME)
        await service.raise_levels(["Pandas"], "valide", _ev("Quiz", "quiz", "q1"))
        await service.upsert_catalog([SkillDraft(name="Polars", domain="Données")], [])
        levels = await service.levels_of(["pandas", "PANDAS", "Polars", "inconnue", ""])
    assert levels == [("Pandas", "valide")]  # « Polars » n'a pas de niveau


async def test_raise_levels_dedups_evidence_by_kind_and_ref(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, ME)
        await service.raise_levels(["Pandas"], "valide", _ev("Quiz : 90 %", "quiz", "q1"))
        await service.raise_levels(["Pandas"], "valide", _ev("Quiz : 85 %", "quiz", "q1"))
        await service.raise_levels(["Pandas"], "valide", _ev("Quiz : 80 %", "quiz", "q2"))
        await service.raise_levels(["Pandas"], "en_cours", _ev("Étude", "study", "q1"))
        await service.raise_levels(["Pandas"], "en_cours", _ev("Programme A", "program", None))
        await service.raise_levels(["Pandas"], "en_cours", _ev("Programme B", "program", None))
        await service.raise_levels(["Pandas"], "en_cours", _ev("Programme A", "program", None))
        await db.commit()
    async with db_session_factory() as db:
        row = (await db.execute(select(UserSkill))).scalar_one()
    assert [e["label"] for e in row.evidence] == [
        "Quiz : 90 %",  # la première preuve d'un couple (genre, référence) est gardée
        "Quiz : 80 %",
        "Étude",
        "Programme A",
        "Programme B",
    ]


async def test_raise_levels_reads_phase4_string_evidence(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        await SkillsService(db, ME).raise_levels(["Pandas"], "en_cours", _ev("Programme P"))
        row = (await db.execute(select(UserSkill))).scalar_one()
        row.evidence = ["Programme Ancien"]  # chaîne écrite avant la phase 5
        await db.commit()
    async with db_session_factory() as db:
        await SkillsService(db, ME).raise_levels(["Pandas"], "valide", _ev("Quiz", "quiz", "q1"))
        await db.commit()
    async with db_session_factory() as db:
        row = (await db.execute(select(UserSkill))).scalar_one()
    assert [(e["kind"], e["label"]) for e in row.evidence] == [
        ("program", "Programme Ancien"),
        ("quiz", "Quiz"),
    ]


async def test_evidence_keeps_the_latest_twenty(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, ME)
        for n in range(25):
            await service.raise_levels(["Pandas"], "en_cours", _ev(f"p{n}", "program", f"p{n}"))
        await db.commit()
    async with db_session_factory() as db:
        row = (await db.execute(select(UserSkill))).scalar_one()
    assert [e["label"] for e in row.evidence] == [f"p{n}" for n in range(5, 25)]


async def test_record_review_demotes_valide_after_two_failures(
    db_session_factory: Factory,
) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, ME)
        await service.raise_levels(["Pandas"], "valide", _ev("quiz", "quiz", "q1"))
        await service.raise_levels(["SQL"], "en_cours", _ev("programme"))
        assert await service.record_review("inconnue", ok=False) is None
        assert await service.record_review("pandas", ok=False) is None
        assert await service.record_review("pandas", ok=True) is None  # série remise à 0
        assert await service.record_review("pandas", ok=False) is None
        assert await service.record_review("PANDAS", ok=False) == "en_cours"
        assert await service.record_review("sql", ok=False) is None
        assert await service.record_review("sql", ok=False) is None  # pas `valide` : rien
        rows = {
            row.skill_id: (row.level, row.fail_streak)
            for row in (await db.execute(select(UserSkill))).scalars()
        }
        assert sorted(rows.values()) == [("en_cours", 0), ("en_cours", 2)]
        await service.reset_fail_streaks(["SQL"])
        assert sorted(r.fail_streak for r in (await db.execute(select(UserSkill))).scalars()) == [
            0,
            0,
        ]
