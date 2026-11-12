"""Compétences et mémoire à la validation (D6, D7, D88) : compétences couvertes « en cours »,
jamais baissées, reflétées dans les acquis de la mémoire ; un reflet manqué est rattrapé par
l'appel suivant (rejeu de `finalize`, second « Valider »), sans doublon. Propriété vérifiée."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.agents.tools.plan_schema import PlanDraft
from app.db.models.memory import MemoryItem, MemoryWrite
from app.db.models.program import PlanVersion, Program
from app.db.models.skills import Skill, UserSkill
from app.features.program.service import validation
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from app.features.program.service.validation import validate_program
from tests.features.program.conftest import Draft
from tests.features.program.support import API, MONDAY, Factory, add_goal, sample_plan

ME = "moi"


async def _accepted(factory: Factory, program_id: str) -> list[PlanVersion]:
    async with factory() as db:
        rows = await db.execute(select(PlanVersion).where(PlanVersion.program_id == program_id))
        return [v for v in rows.scalars() if v.accepted_at is not None]


async def _draft(
    store: AgentProgramStore, factory: Factory, user_id: str = ME, plan: PlanDraft | None = None
) -> str:
    rows = await add_goal(factory, user_id)
    saved = await store.save_draft(
        user_id,
        "s1",
        rows.goal_id,
        plan or sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="v1",
    )
    return saved.program_id


async def _levels(factory: Factory, user_id: str = ME) -> dict[str, str]:
    async with factory() as db:
        stmt = select(Skill.norm_name, UserSkill.level).join(
            UserSkill, UserSkill.skill_id == Skill.id
        )
        return {
            row[0]: row[1] for row in (await db.execute(stmt.where(Skill.user_id == user_id))).all()
        }


async def _acquis(factory: Factory, title: str, user_id: str = ME) -> MemoryItem:
    async with factory() as db:
        stmt = select(MemoryItem).where(
            MemoryItem.user_id == user_id, MemoryItem.kind == "acquis", MemoryItem.title == title
        )
        return (await db.execute(stmt)).scalar_one()


async def test_validation_sets_skills_in_progress_and_reflects_memory(
    store: AgentProgramStore, program_rt: ProgramRuntime, db_session_factory: Factory
) -> None:
    program_id = await _draft(store, db_session_factory)
    await store.validate(ME, "s1", program_id)
    levels = await _levels(db_session_factory)
    assert levels["pandas"] == "en_cours" and levels["numpy"] == "en_cours"
    assert (await _acquis(db_session_factory, "pandas")).meta["level"] == "en_cours"
    async with db_session_factory() as db:
        program = await db.get(Program, program_id)
        assert program is not None and program.status == "validated"
        assert program.validated_at is not None
        writes = (await db.execute(select(MemoryWrite).where(MemoryWrite.user_id == ME))).scalars()
        assert {(w.author, w.session_id) for w in writes} == {("strategist", "s1")}
    await store.validate(ME, "s1", program_id)  # rejoué : rien de plus
    assert len(await _accepted(db_session_factory, program_id)) == 1


async def test_validation_never_lowers_a_level(
    store: AgentProgramStore, program_rt: ProgramRuntime, db_session_factory: Factory
) -> None:
    async with db_session_factory() as db:
        skill = Skill(user_id=ME, name="pandas", norm_name="pandas", synonyms=[])
        db.add(skill)
        await db.flush()
        db.add(UserSkill(user_id=ME, skill_id=skill.id, level="valide", evidence=["Quiz réussi"]))
        db.add(
            MemoryItem(
                user_id=ME,
                kind="acquis",
                title="pandas",
                text="Pandas validé par un quiz.",
                created_by="user",
                content_hash="h-pandas",
                meta={"level": "valide"},
            )
        )
        await db.commit()
    plan = sample_plan()
    plan.weeks[0].modules[0].skills = ["pandas", "polars"]  # couvert, pas entièrement acquis
    program_id = await _draft(store, db_session_factory, plan=plan)
    await validate_program(program_rt, ME, program_id, session_id=None)
    levels = await _levels(db_session_factory)
    assert levels == {"pandas": "valide", "polars": "en_cours", "numpy": "en_cours"}
    assert (await _acquis(db_session_factory, "pandas")).meta["level"] == "valide"
    polars = await _acquis(db_session_factory, "polars")
    assert polars.meta["level"] == "en_cours" and polars.created_by == "user"


async def test_validate_checks_ownership(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    program_id = await _draft(store, db_session_factory)
    for user_id, session_id in (("autre", "s1"), (ME, "autre-session")):
        with pytest.raises(Exception) as caught:
            await store.validate(user_id, session_id, program_id)
        assert getattr(caught.value, "code", None) == "program_not_found"


async def _acquis_count(factory: Factory) -> tuple[int, int]:
    async with factory() as db:
        items = await db.execute(
            select(func.count()).select_from(MemoryItem).where(MemoryItem.kind == "acquis")
        )
        writes = await db.execute(select(func.count()).select_from(MemoryWrite))
        return int(items.scalar_one()), int(writes.scalar_one())


async def test_missed_reflection_is_caught_up_by_the_next_call(
    store: AgentProgramStore,
    db_session_factory: Factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = validation.reflect_skill_levels
    calls: list[int] = []

    async def failing_once(*args: Any, **kwargs: Any) -> list[str]:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database is locked")
        return await real(*args, **kwargs)

    monkeypatch.setattr(validation, "reflect_skill_levels", failing_once)
    program_id = await _draft(store, db_session_factory)
    await store.validate(ME, "s1", program_id)  # validé, reflet manqué
    assert (await _levels(db_session_factory))["pandas"] == "en_cours"
    assert await _acquis_count(db_session_factory) == (0, 0)
    await store.validate(ME, "s1", program_id)  # rejeu de `finalize` : rattrapé
    assert (await _acquis(db_session_factory, "pandas")).meta["level"] == "en_cours"
    assert (await _acquis(db_session_factory, "numpy")).meta["level"] == "en_cours"
    assert await _acquis_count(db_session_factory) == (2, 2)
    for _ in range(2):  # rejoué encore : aucun doublon, aucune écriture de plus
        await store.validate(ME, "s1", program_id)
    assert await _acquis_count(db_session_factory) == (2, 2)
    assert len(await _accepted(db_session_factory, program_id)) == 1


async def test_second_validate_route_catches_up_a_missed_reflection(
    client: httpx.AsyncClient,
    app: FastAPI,
    draft_program: Draft,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = validation.reflect_skill_levels

    async def broken(*args: Any, **kwargs: Any) -> list[str]:
        raise RuntimeError("panne")

    monkeypatch.setattr(validation, "reflect_skill_levels", broken)
    url = f"{API}/programs/{draft_program.program_id}/validate"
    assert (await client.post(url)).json()["status"] == "validated"
    factory = app.state.session_factory
    assert await _acquis_count(factory) == (0, 0)
    monkeypatch.setattr(validation, "reflect_skill_levels", real)
    assert (await client.post(url)).json()["status"] == "validated"
    user = draft_program.user_id
    assert (await _acquis(factory, "pandas", user)).meta["level"] == "en_cours"
    assert (await _acquis_count(factory))[0] == 2
