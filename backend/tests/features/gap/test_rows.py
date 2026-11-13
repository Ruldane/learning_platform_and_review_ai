"""Lignes de l'écart (D122), recalculées à chaque lecture : niveaux actuels (nom rattaché, sinon
nom du besoin), hors périmètre, module d'un programme validé avec la semaine de sa 1re tâche,
mots clés des revues de CV (G3) hors du score."""

from datetime import UTC, datetime

from app.agents.tools.gap_port import SkillMatch
from app.agents.tools.plan_schema import SkillDraft
from app.core.skills import evidence
from app.db.models.career import CvReview
from app.db.models.postings import JobPosting
from app.db.models.skills import SkillLevel
from app.features.gap.service.rows import gap_rows
from app.features.gap.service.score import GapRow, match_score
from app.features.postings.service.agent_store import AgentGapStore
from app.features.skills.service import SkillsService
from tests.features.gap.conftest import add_program
from tests.features.postings.conftest import ME, add_posting, analysis, fresh
from tests.features.program.support import Factory
from tests.support.gap import LEVELS, MATCHES

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)


async def set_levels(factory: Factory, levels: dict[str, SkillLevel | None]) -> None:
    async with factory() as db:
        skills = SkillsService(db, ME)
        for name, level in levels.items():
            if level is None:
                await skills.upsert_catalog([SkillDraft(name=name, domain="Outils")], [])
            else:
                await skills.raise_levels([name], level, evidence("quiz", name, name, NOW))
        await db.commit()


async def ready_posting(store: AgentGapStore, factory: Factory, **over: object) -> JobPosting:
    posting_id = await add_posting(factory)
    found = analysis(**over)
    await store.save_analysis(ME, "s1", posting_id, found)
    names = {need.name for need in found.skills}
    matches = [SkillMatch(need=n, known=k) for n, k in MATCHES.items() if n in names]
    matches += [SkillMatch(need=n, known=None) for n in names - set(MATCHES)]
    await store.save_gap(ME, "s1", posting_id, matches)
    return await fresh(factory, posting_id)


async def rows_of(factory: Factory, posting: JobPosting) -> dict[str, GapRow]:
    async with factory() as db:
        return {row.skill: row for row in await gap_rows(db, ME, posting)}


async def test_gap_rows_follow_current_levels(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await set_levels(db_session_factory, LEVELS)
    posting = await ready_posting(store, db_session_factory)
    rows = await rows_of(db_session_factory, posting)
    assert rows["RAG"] == GapRow("RAG", True, "valide", "to_add", None)  # nom rattaché
    assert rows["LangGraph"].level is None and match_score(list(rows.values())) == 62
    # LangGraph, entré au référentiel sans niveau par `save_gap`, est appris ensuite.
    await set_levels(db_session_factory, {"LangGraph": "en_cours"})
    rows = await rows_of(db_session_factory, posting)
    assert rows["LangGraph"].level == "en_cours" and match_score(list(rows.values())) == 66


async def test_gap_row_in_program_has_week(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await set_levels(db_session_factory, LEVELS)
    await add_program(
        db_session_factory, ME,
        [
            (["LangGraph"], 1, 2, False),  # 1re tâche en semaine 2
            (["Génération augmentée par recherche"], 3, 3, False),  # nom rattaché à « RAG »
            (["Intégration continue"], 1, 1, True),  # module sauté
        ],
    )  # fmt: skip
    await add_program(
        db_session_factory, ME, [(["Évaluation de RAG"], 1, 1, False)], status="draft"
    )
    posting = await ready_posting(store, db_session_factory)
    rows = await rows_of(db_session_factory, posting)
    assert (rows["LangGraph"].action, rows["LangGraph"].week) == ("in_program", 2)
    assert (rows["RAG"].action, rows["RAG"].week) == ("in_program", 3)
    assert (rows["Intégration continue"].action, rows["Intégration continue"].week) == (
        "to_add", None,
    )  # fmt: skip
    assert rows["Évaluation de RAG"].action == "to_add"


async def test_not_learnable_is_out_of_scope(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await add_program(db_session_factory, ME, [(["Permis B"], 1, 1, False)])
    skills = [
        {"name": "Permis B", "required": True, "domain": None, "learnable": False},
        {"name": "Python", "required": True, "domain": None, "learnable": True},
    ]
    posting = await ready_posting(store, db_session_factory, skills=skills)
    rows = await rows_of(db_session_factory, posting)
    assert rows["Permis B"] == GapRow("Permis B", True, None, "out_of_scope", None)


async def test_review_keywords_join_the_gap_outside_the_score(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await set_levels(db_session_factory, LEVELS)
    posting = await ready_posting(store, db_session_factory)
    async with db_session_factory() as db:
        db.add(
            CvReview(
                user_id=ME, posting_id=posting.id, template_id="t", profile_version=1,
                status="done",
                keywords_to_gap=["AWS", "python", {"term": "Génération augmentée par recherche"},
                                 "aws", {"term": "Terraform"}],
            )
        )  # fmt: skip
        await db.commit()
    async with db_session_factory() as db:
        rows = await gap_rows(db, ME, posting)
    added = [row for row in rows if row.source == "cv_review"]
    assert added == [
        GapRow("AWS", False, None, "to_add", None, "cv_review"),
        GapRow("Terraform", False, None, "to_add", None, "cv_review"),
    ]
    assert match_score(rows) == 62


async def test_no_rows_before_the_gap(store: AgentGapStore, db_session_factory: Factory) -> None:
    posting_id = await add_posting(db_session_factory)
    await store.save_analysis(ME, "s1", posting_id, analysis())
    assert await rows_of(db_session_factory, await fresh(db_session_factory, posting_id)) == {}
