"""Le vrai port de l'écart (`AgentGapStore`, D121, D122) : offre lue, analyse posée une fois et
élément de mémoire `offre` indexé, refus idempotent, référentiel ordonné, écart rangé une fois par
session avec les besoins sans rattachement ajoutés au référentiel (domaine par défaut)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.agents.tools.gap_port import GapSaved, KnownSkill, SkillMatch
from app.agents.tools.plan_schema import SkillDraft
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.models.memory import MemoryItem
from app.db.models.skills import Skill, SkillLevel
from app.features.postings.service.agent_store import AgentGapStore
from app.features.skills.service import SkillsService
from tests.features.postings.conftest import ME, add_posting, analysis, fresh
from tests.features.program.support import Factory
from tests.support.gap import LEVELS, MATCHES

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)


async def set_levels(factory: Factory, levels: dict[str, SkillLevel | None]) -> None:
    async with factory() as db:
        skills = SkillsService(db, ME)
        for name, level in levels.items():
            if level is None:  # au référentiel, sans niveau
                await skills.upsert_catalog([SkillDraft(name=name, domain="Outils")], [])
            else:
                await skills.raise_levels([name], level, evidence("quiz", name, name, NOW))
        await db.commit()


def matches() -> list[SkillMatch]:
    return [SkillMatch(need=need, known=known) for need, known in MATCHES.items()]


async def test_posting_is_read_and_scoped(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory, url="https://exemple.org/o", url_norm="k")
    view = await store.posting(ME, posting_id)
    assert (view.posting_id, view.url, view.analysis, view.status) == (
        posting_id, "https://exemple.org/o", None, "analyzing",
    )  # fmt: skip
    with pytest.raises(AppError) as caught:
        await store.posting("autre", posting_id)
    assert caught.value.code == "posting_not_found"


async def test_save_analysis_is_idempotent(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory)
    first = await store.save_analysis(ME, "s1", posting_id, analysis(company="Société Fictive SAS"))
    second = await store.save_analysis(ME, "s2", posting_id, analysis(title="Autre titre"))
    assert first.first and not second.first
    assert second.analysis.title == "AI Product Engineer"  # celle qui est rangée
    row = await fresh(db_session_factory, posting_id)
    assert (row.status, row.title, row.company, row.company_norm) == (
        "ready", "AI Product Engineer", "Société Fictive SAS", "societe fictive",
    )  # fmt: skip
    async with db_session_factory() as db:
        items = list((await db.execute(select(MemoryItem))).scalars())
    assert [(i.id, i.kind, i.title, i.created_by) for i in items] == [
        (row.memory_item_id, "offre", "AI Product Engineer — Société Fictive SAS", "analyst")
    ]
    assert items[0].indexed_at is not None and items[0].text.startswith("AI Product Engineer")


async def test_save_analysis_does_not_touch_the_referential(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory)
    await store.save_analysis(ME, "s1", posting_id, analysis())
    assert await store.known_skills(ME) == []


async def test_reject_keeps_the_first_reason(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory)
    await store.reject(ME, posting_id, "Pas une offre.")
    await store.reject(ME, posting_id, "Autre raison.")
    row = await fresh(db_session_factory, posting_id)
    assert (row.status, row.failure_reason) == ("rejected", "Pas une offre.")


async def test_known_skills_are_ordered_with_levels(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await set_levels(
        db_session_factory, {"Kubernetes": None, "Docker": "declared", "Python": "validated"}
    )
    assert await store.known_skills(ME) == [
        KnownSkill("Python", "validated"),
        KnownSkill("Docker", "declared"),
        KnownSkill("Kubernetes", None),
    ]


async def test_save_gap_once_per_session_and_adds_unmatched_needs(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await set_levels(db_session_factory, LEVELS)
    posting_id = await add_posting(db_session_factory)
    await store.save_analysis(ME, "s1", posting_id, analysis())
    saved = await store.save_gap(ME, "s1", posting_id, matches())
    assert saved == GapSaved(score=62, rows=10, missing=4, missing_required=2)
    row = await fresh(db_session_factory, posting_id)
    assert row.gap is not None and row.gap["session_id"] == "s1"
    async with db_session_factory() as db:
        added = {
            s.name: s.domain
            for s in (await db.execute(select(Skill))).scalars()
            if s.name not in LEVELS
        }
    assert added == {
        "LangGraph": "Autres",
        "Évaluation de RAG": "Autres",
        "Intégration continue": "Autres",
        "Anglais professionnel": "Autres",
    }
    # Rejeu : rien de plus ; les compétences ajoutées restent sans niveau.
    assert await store.save_gap(ME, "s1", posting_id, []) == saved
    assert (await fresh(db_session_factory, posting_id)).gap == row.gap
    known = await store.known_skills(ME)
    assert len(known) == len(LEVELS) + 4 and KnownSkill("LangGraph", None) in known


async def test_save_gap_uses_the_need_domain(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory)
    skills = [{"name": "Rust", "required": True, "domain": "Langages", "learnable": True}]
    await store.save_analysis(ME, "s1", posting_id, analysis(skills=skills))
    saved = await store.save_gap(ME, "s1", posting_id, [SkillMatch(need="Rust", known=None)])
    assert saved == GapSaved(score=0, rows=1, missing=1, missing_required=1)
    async with db_session_factory() as db:
        assert [(s.name, s.domain) for s in (await db.execute(select(Skill))).scalars()] == [
            ("Rust", "Langages")
        ]


async def test_save_gap_needs_an_analysis(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory)
    with pytest.raises(AppError) as caught:
        await store.save_gap(ME, "s1", posting_id, [])
    assert caught.value.code == "posting_not_analyzed"


async def test_unlearnable_needs_never_enter_the_referential(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    posting_id = await add_posting(db_session_factory)
    skills = [
        {"name": "Rust", "required": True, "domain": "Langages", "learnable": True},
        {"name": "Permis B", "required": True, "domain": None, "learnable": False},
        {"name": "Bac+5", "required": False, "domain": None, "learnable": False},
    ]
    await store.save_analysis(ME, "s1", posting_id, analysis(skills=skills))
    await store.save_gap(ME, "s1", posting_id, [SkillMatch(need="Rust", known=None)])
    async with db_session_factory() as db:
        names = [s.name for s in (await db.execute(select(Skill))).scalars()]
    assert names == ["Rust"]
    assert await store.known_skills(ME) == [KnownSkill("Rust", None)]
