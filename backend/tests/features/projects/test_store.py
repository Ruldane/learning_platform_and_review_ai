"""Le port réel des parcours `project_brief` et `project_review` (`AgentProjectStore`, D165, D166) :
entrées lues en base, énoncé et évaluation rangés une seule fois par session, compétences du module
montées à `prouve`, journal, reflet en mémoire, `prouve` jamais baissé par des fiches ratées."""

import httpx
import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.core.providers import MemoryProviders
from app.db.models.learning import Goal
from app.db.models.skills import Skill, UserSkill
from app.features.projects.service.screenshots import detect_image
from app.features.projects.service.store import AgentProjectStore
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillsService
from tests.features.projects.support import NOW, WEBP, Env, draft_results, outcome
from tests.features.radar.support import doc
from tests.features.study.conftest import SKILLS
from tests.support.lessons import lesson_markdown
from tests.support.memory import FakeWebReader
from tests.support.projects import DESCRIPTION, REPO_URL, TITLE, sample_brief


@pytest.fixture
def store(env: Env) -> AgentProjectStore:
    return AgentProjectStore(env.rt)


async def _validate(env: Env, store: AgentProjectStore, *, session: str = "s-review") -> str:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await store.save_review(env.user_id, session, pid, outcome())
    return pid


async def test_brief_inputs_read_the_module_and_the_week(
    env: Env, store: AgentProjectStore
) -> None:
    pid = await env.add_project(brief=False, status="brief_pending")
    inputs = await store.brief_inputs(env.user_id, pid)
    assert inputs.module_title == "Module Bases" and inputs.skills == SKILLS
    assert inputs.prerequisites == [] and inputs.week_deliverable == "Un dépôt"
    assert inputs.lesson_excerpt == lesson_markdown(400)[:3000] and inputs.language == "en"
    assert inputs.role is None


async def test_brief_inputs_role_and_lesson_excerpt(env: Env, store: AgentProjectStore) -> None:
    pid = await env.add_project(brief=False, status="brief_pending")
    async with env.app.state.session_factory() as db:
        db.add(
            Goal(
                user_id=env.user_id,
                text="Devenir ingénieure",
                framing={},
                target_role="Ingénieure IA",
            )
        )
        await db.commit()
    assert (await store.brief_inputs(env.user_id, pid)).role == "Ingénieure IA"
    async with env.app.state.session_factory() as db:
        service = SettingsService(db, env.user_id)
        current = await service.get()
        await service.replace(current.model_copy(update={"radar_role": "Développeuse Python"}))
        await db.commit()
    assert (await store.brief_inputs(env.user_id, pid)).role == "Développeuse Python"


async def test_save_brief_once_and_the_project_is_todo(env: Env, store: AgentProjectStore) -> None:
    pid = await env.add_project(brief=False, status="brief_pending", title="Module Bases")
    brief = sample_brief()
    await store.save_brief(env.user_id, "s1", pid, brief)
    row = await env.row(pid)
    assert (row.status, row.title, row.session_id) == ("todo", TITLE, None)
    assert row.brief == brief.model_dump(mode="json")
    await store.save_brief(env.user_id, "s1", pid, sample_brief(title="Un autre énoncé"))
    assert (await env.row(pid)).brief == brief.model_dump(mode="json")  # la première gagne


async def test_brief_failed_is_final_only_on_the_last_attempt(
    env: Env, store: AgentProjectStore
) -> None:
    pid = await env.add_project(brief=False, status="brief_pending", brief_attempts=2)
    await store.brief_failed(env.user_id, "s1", pid, "structured_output_invalid")
    assert (await env.row(pid)).status == "brief_pending"  # la tâche relancera un essai
    await env.patch(pid, brief_attempts=3)
    await store.brief_failed(env.user_id, "s1", pid, "structured_output_invalid")
    assert (await env.row(pid)).status == "brief_failed"


async def test_review_inputs_carry_the_last_submission_and_the_profile(
    env: Env, store: AgentProjectStore
) -> None:
    older = {"at": NOW.isoformat(), "repo_url": None, "description": "Ancien", "screenshots": []}
    last = {**older, "repo_url": REPO_URL, "description": DESCRIPTION, "screenshots": ["k1", "k2"]}
    pid = await env.add_project(status="reviewing", submissions=[older, last])
    assert (await store.review_inputs(env.user_id, pid)).profile is None
    await env.add_profile(1)
    inputs = await store.review_inputs(env.user_id, pid)
    assert (inputs.repo_url, inputs.description, inputs.screenshots) == (REPO_URL, DESCRIPTION, 2)
    assert inputs.title == TITLE and inputs.brief == sample_brief() and inputs.skills == SKILLS
    assert inputs.profile is not None and inputs.language == "en"


async def test_repo_text_reads_one_page_and_unreadable_is_none(
    env: Env, store: AgentProjectStore, memory_providers: MemoryProviders
) -> None:
    web = memory_providers.web
    assert isinstance(web, FakeWebReader)
    web.pages[REPO_URL] = doc(REPO_URL, "# Suivi de lecture\nUne API de suivi de lecture.")
    text = await store.repo_text(env.user_id, "s1", REPO_URL)
    assert text is not None and "Suivi de lecture" in text
    assert await store.repo_text(env.user_id, "s1", "https://example.org/inconnu") is None
    assert await store.repo_text(env.user_id, "s1", "pas un lien") is None  # lien refusé


async def test_validation_raises_module_skills_to_prouve(
    env: Env, store: AgentProjectStore
) -> None:
    pid = await _validate(env, store)
    levels = await env.levels(*SKILLS)
    assert set(levels) == set(SKILLS)
    assert all(level == "proven" and "project" in kinds for level, kinds in levels.values())
    row = await env.row(pid)
    assert row.status == "validated" and row.validated_at == NOW
    assert row.evaluation is not None and row.evaluation["verdict"] == "validated"
    assert [d["status"] for d in row.drafts.values()] == ["ready"] * 4
    assert list(row.drafts) == ["cv_line", "profile_entry", "linkedin_post", "readme_plan"]
    assert row.profile_version is None  # jamais d'entrée au profil à la validation


async def test_validation_reflects_levels_in_memory_and_writes_the_journal(
    env: Env, store: AgentProjectStore, client: httpx.AsyncClient
) -> None:
    pid = await _validate(env, store)
    acquis = (await client.get("/api/v1/memory/items", params={"kind": "skill"})).json()
    assert {item["title"] for item in acquis["items"]} >= set(SKILLS)
    journal = (await client.get("/api/v1/journal", params={"kind": "project"})).json()
    [entry] = journal["entries"]
    assert entry["kind"] == "project" and entry["text"] == f"Project validated: {TITLE}"
    assert entry["occurred_on"] == "2026-11-24"
    assert entry["links"]["session_id"] == "s-review"
    assert pid


async def test_failed_cards_do_not_demote_prouve(env: Env, store: AgentProjectStore) -> None:
    await _validate(env, store)
    async with env.app.state.session_factory() as db:
        skills = SkillsService(db, env.user_id)
        for _ in range(3):  # bien au-delà des deux échecs de suite
            assert await skills.record_review("pandas", False) is None
        await db.commit()
    assert (await env.levels("pandas"))["pandas"][0] == "proven"


async def test_save_review_replay_writes_once(
    env: Env, store: AgentProjectStore, client: httpx.AsyncClient
) -> None:
    pid = await _validate(env, store)
    first = await env.row(pid)
    await store.save_review(
        env.user_id, "s-review", pid, outcome(drafts=draft_results(to_check=["cv_line"]))
    )
    await store.save_review(
        env.user_id, "autre-session", pid, outcome((False, False, False, False))
    )
    row = await env.row(pid)
    assert (row.status, row.evaluation, row.drafts, row.validated_at) == (
        "validated",
        first.evaluation,
        first.drafts,
        first.validated_at,
    )
    journal = (await client.get("/api/v1/journal", params={"kind": "project"})).json()
    assert len(journal["entries"]) == 1
    async with env.app.state.session_factory() as db:
        stmt = select(UserSkill.evidence).join(Skill, Skill.id == UserSkill.skill_id)
        stmt = stmt.where(Skill.user_id == env.user_id, Skill.name == "pandas")
        evidence = (await db.execute(stmt)).scalar_one()
    assert len(evidence) == 1 and evidence[0]["ref_id"] == pid
    assert evidence[0]["label"] == f"Project '{TITLE}' validated (24/11)"


async def test_to_redo_outcome_keeps_no_drafts_and_raises_nothing(
    env: Env, store: AgentProjectStore
) -> None:
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await store.save_review(
        env.user_id, "s1", pid, outcome((True, False, True, True), repo="unreadable")
    )
    row = await env.row(pid)
    assert row.status == "to_redo" and row.drafts == {} and row.validated_at is None
    assert row.evaluation is not None and row.evaluation["repo_status"] == "unreadable"
    assert [r["met"] for r in row.evaluation["results"]] == [True, False, True, True]
    assert not await env.levels(*SKILLS)


async def test_an_evaluation_that_nobody_waits_for_is_ignored(
    env: Env, store: AgentProjectStore
) -> None:
    pid = await env.add_project()  # `todo` : aucun rendu en cours d'évaluation
    await store.save_review(env.user_id, "s1", pid, outcome())
    row = await env.row(pid)
    assert row.status == "todo" and row.evaluation is None and row.drafts == {}
    assert not await env.levels(*SKILLS)
    other = await env.add_project(
        1, status="reviewing", submissions=[env.last_submission()], session_id="s-bonne"
    )
    await store.save_review(env.user_id, "s-ancienne", other, outcome())  # une autre session
    assert (await env.row(other)).status == "reviewing"


async def test_the_verdict_is_the_codes_not_the_outcomes(
    env: Env, store: AgentProjectStore
) -> None:
    """Un résultat sur trois seulement ne valide jamais, même si l'issue le dit."""
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    bad = outcome()
    bad = type(bad)(bad.verdict, bad.results[:3], bad.feedback, bad.repo_status, bad.drafts)
    await store.save_review(env.user_id, "s1", pid, bad)
    row = await env.row(pid)
    assert row.status == "to_redo" and row.drafts == {} and not await env.levels(*SKILLS)


async def test_a_validated_outcome_without_drafts_is_kept_validated(
    env: Env, store: AgentProjectStore
) -> None:
    """Les brouillons indisponibles (premier appel en échec) ne coûtent pas la validation (D173)."""
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await store.save_review(env.user_id, "s1", pid, outcome(drafts=[]))
    row = await env.row(pid)
    assert row.status == "validated" and row.drafts == {} and row.validated_at == NOW
    assert await env.levels(*SKILLS)


async def test_a_stray_result_index_never_validates_what_the_graph_judged_to_redo(
    env: Env, store: AgentProjectStore
) -> None:
    """Le parcours juge « à reprendre » (un résultat hors énoncé) : le port reçoit les 4 résultats
    rangés, tous atteints, mais ne valide pas (D173) : ni brouillons, ni compétence prouvée."""
    pid = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    good = outcome()
    judged = type(good)("to_redo", good.results, good.feedback, good.repo_status, None)
    await store.save_review(env.user_id, "s1", pid, judged)
    row = await env.row(pid)
    assert row.status == "to_redo" and row.drafts == {} and row.validated_at is None
    assert row.evaluation is not None and row.evaluation["verdict"] == "to_redo"
    assert not await env.levels(*SKILLS)


async def test_other_users_project_is_unknown_to_the_port(
    env: Env, store: AgentProjectStore
) -> None:
    pid = await env.add_project()
    with pytest.raises(AppError) as caught:
        await store.review_inputs("autre-utilisatrice", pid)
    assert caught.value.code == "project_not_found"


def test_webp_signature_is_recognised() -> None:
    assert detect_image(WEBP) == "image/webp" and detect_image(b"RIFF....WAVE....") is None


def test_bare_jpeg_header_refused() -> None:
    """Quatre octets (signature et marqueur) ne font pas une image : le marqueur annonce un
    segment, dont la longueur sur deux octets manque (8.10, D181)."""
    assert detect_image(b"\xff\xd8\xff\xe0") is None
    assert detect_image(b"\xff\xd8\xff\xdb") is None and detect_image(b"\xff\xd8\xff\xfe") is None
    assert detect_image(b"\xff\xd8\xff\xe0\x00") is None
    assert detect_image(b"\xff\xd8\xff\xe0\x00\x10") == "image/jpeg"


def test_a_jpeg_needs_more_than_its_three_byte_signature() -> None:
    assert detect_image(b"\xff\xd8\xff") is None and detect_image(b"\xff\xd8\xff\x00") is None
    assert detect_image(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "image/jpeg"
