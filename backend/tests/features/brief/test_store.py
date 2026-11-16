"""Port réel du brief (`AgentBriefStore`, D161, D162) : faits du conseil tirés des rubriques,
nombres permis en chiffres, sujet de la ressource, écritures conditionnelles (la première gagne),
accès d'un autre utilisateur refusé."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app.agents.tools.brief_schema import ResourceView
from app.core.errors import AppError
from app.db.models.learning import Goal
from app.db.models.program import Program
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.store import AgentBriefStore
from app.features.brief.service.topic import MAX_TOPIC, goal_topic
from app.features.settings.service import SettingsService
from tests.features.brief.conftest import NOW, OTHER, TODAY, Env
from tests.features.brief.support import add_cards, add_run, add_user, applied, briefs, posting
from tests.features.study.conftest import seed

VIEW = ResourceView(
    "Guide fictif", "https://docs.example.org/g", "docs.example.org", None, "Utile."
)
SENTENCES = ["Commence par ton bloc du jour.", "Puis passe tes fiches en revue."]


async def _brief(env: Env) -> str:
    brief, _ = await ensure_today(env.rt, env.user_id, origin="opening")
    return brief.id


async def _settings(env: Env, **fields: object) -> None:
    async with env.rt.session_factory() as db:
        service = SettingsService(db, env.user_id)
        await service.replace((await service.get()).model_copy(update=fields))
        await db.commit()


async def test_context_facts_come_from_the_rubrics(client: httpx.AsyncClient, env: Env) -> None:
    await seed(env.app)
    env.at(NOW)
    await add_cards(env, 2)
    await applied(client, 8)
    await add_run(env, [posting(1, 88), posting(2, 75)])
    brief_id = await _brief(env)
    ctx = await AgentBriefStore(env.rt).context(env.user_id, brief_id)
    assert (ctx.brief_id, ctx.day, ctx.language) == (brief_id, TODAY, "fr")
    f = ctx.facts
    assert (f.block_title, f.block_minutes) == ("Leçon Module Bases", 285)
    assert (f.cards_due, f.reminders_due, f.offers) == (2, 1, 2)
    assert (f.week_planned, f.week_done, f.streak_days, f.best_score) == (7, 0, 0, None)
    assert (ctx.resource_done, ctx.advice_done) == (False, False)


async def test_allowed_numbers_are_the_digits_of_the_facts_only(
    client: httpx.AsyncClient, env: Env
) -> None:
    await seed(env.app)
    env.at(NOW)
    await add_cards(env, 2)
    ctx = await AgentBriefStore(env.rt).context(env.user_id, await _brief(env))
    assert ctx.allowed_numbers == frozenset({"285", "2", "0", "7"})  # minutes, fiches, relances…
    assert all(number.isdigit() for number in ctx.allowed_numbers)
    assert isinstance(ctx.allowed_numbers, frozenset)


async def test_empty_brief_has_zero_facts_and_no_block(env: Env) -> None:
    ctx = await AgentBriefStore(env.rt).context(env.user_id, await _brief(env))
    assert ctx.facts.block_title is None and ctx.facts.block_minutes == 0
    assert (ctx.facts.cards_due, ctx.facts.week_planned, ctx.facts.streak_days) == (0, 0, 0)
    assert ctx.allowed_numbers == frozenset({"0"})


async def _goal(env: Env, text: str, role: str | None = None) -> None:
    async with env.rt.session_factory() as db:
        db.add(Goal(user_id=env.user_id, text=text, target_role=role, framing={}, status="chosen"))
        await db.commit()


async def _topic(env: Env, brief_id: str) -> str | None:
    return (await AgentBriefStore(env.rt).context(env.user_id, brief_id)).topic


async def test_topic_is_none_without_role_goal_or_program(env: Env) -> None:
    assert await _topic(env, await _brief(env)) is None


async def test_topic_prefers_the_radar_role_then_the_goal_role(env: Env) -> None:
    brief_id = await _brief(env)
    await _goal(env, "Devenir data engineer", "Ingénieur données")
    assert await _topic(env, brief_id) == "Ingénieur données actualités"
    await _settings(env, radar_role="Ingénieur IA")
    assert await _topic(env, brief_id) == "Ingénieur IA actualités"


async def test_topic_falls_back_to_the_goal_text_without_a_role(env: Env) -> None:
    brief_id = await _brief(env)
    await _goal(env, "Devenir data engineer", None)
    assert await _topic(env, brief_id) == "data engineer actualités"
    await _goal(env, "Become  a\nplatform engineer. Je veux surtout du cloud.")
    assert await _topic(env, brief_id) == "platform engineer actualités"


async def test_topic_falls_back_to_the_validated_program_title(env: Env) -> None:
    await seed(env.app)  # objectif sans poste ; programme validé
    brief_id = await _brief(env)
    async with env.rt.session_factory() as db:
        await db.execute(update(Goal).values(text="Devenir", target_role=None))
        title = (await db.execute(select(Program.title))).scalar_one()
        await db.commit()
    assert await _topic(env, brief_id) == f"{title} actualités"
    async with env.rt.session_factory() as db:
        await db.execute(update(Program).values(status="draft"))
        await db.commit()
    assert await _topic(env, brief_id) is None  # un brouillon n'est pas un programme validé


@pytest.mark.parametrize(
    ("text", "topic"),
    [
        ("Devenir ingénieur IA", "ingénieur IA"),
        ("  devenir  un ingénieur\tIA  ", "ingénieur IA"),
        ("Devenir l'ingénieur IA de mon équipe", "ingénieur IA de mon équipe"),
        ("Become an AI engineer; then lead a team", "AI engineer"),
        ("Passer en data science", "Passer en data science"),
        ("Devenir", None),
        ("Become a", None),
        ("   ", None),
    ],
)
def test_goal_topic_strips_the_verb_and_keeps_one_short_line(text: str, topic: str | None) -> None:
    assert goal_topic(text) == topic


def test_goal_topic_is_capped_on_a_word() -> None:
    topic = goal_topic("Devenir " + "développeur " * 20)
    assert topic is not None and len(topic) <= MAX_TOPIC and "\n" not in topic
    assert not topic.endswith(" ") and topic.split(" ")[-1] == "développeur"


async def test_language_follows_the_lesson_language(env: Env) -> None:
    brief_id = await _brief(env)
    await _settings(env, lesson_language="en")
    assert (await AgentBriefStore(env.rt).context(env.user_id, brief_id)).language == "en"


async def test_resource_first_write_wins_and_empty_counts_as_done(env: Env) -> None:
    store, brief_id = AgentBriefStore(env.rt), await _brief(env)
    await store.save_resource(env.user_id, "s", brief_id, None)  # rubrique vide
    assert (await store.context(env.user_id, brief_id)).resource_done is True
    await store.save_resource(env.user_id, "s", brief_id, VIEW)  # ignorée : la première gagne
    assert (await briefs(env))[0].resource == {}
    other = AgentBriefStore(env.rt)
    second = await _brief_of_day(env, 1)
    await other.save_resource(env.user_id, "s", second, VIEW)
    await other.save_resource(env.user_id, "s", second, None)  # ignorée aussi
    assert (await briefs(env))[1].resource == {
        "title": "Guide fictif",
        "url": "https://docs.example.org/g",
        "domain": "docs.example.org",
        "published": None,
        "why": "Utile.",
    }


async def _brief_of_day(env: Env, offset: int) -> str:
    env.at(NOW + timedelta(days=offset))
    return await _brief(env)


async def test_advice_first_write_wins(env: Env) -> None:
    store, brief_id = AgentBriefStore(env.rt), await _brief(env)
    await store.save_advice(env.user_id, "s", brief_id, SENTENCES)
    await store.save_advice(env.user_id, "s", brief_id, None)  # ignorée : jamais rétrogradé
    await store.save_advice(env.user_id, "s", brief_id, ["Autre conseil, bien plus tard.", "Non."])
    [row] = await briefs(env)
    assert (row.advice, row.advice_status) == ({"sentences": SENTENCES}, "ready")
    assert (await store.context(env.user_id, brief_id)).advice_done is True


@pytest.mark.parametrize(("unavailable", "status"), [(False, "failed"), (True, "unavailable")])
async def test_advice_none_is_final_for_the_day(env: Env, unavailable: bool, status: str) -> None:
    store, brief_id = AgentBriefStore(env.rt), await _brief(env)
    await store.save_advice(env.user_id, "s", brief_id, None, unavailable=unavailable)
    await store.save_advice(env.user_id, "s", brief_id, SENTENCES)  # aucun nouvel essai
    await store.save_advice(env.user_id, "s", brief_id, None, unavailable=not unavailable)
    [row] = await briefs(env)
    assert (row.advice, row.advice_status) == (None, status)
    assert (await store.context(env.user_id, brief_id)).advice_done is True


async def test_another_user_cannot_read_or_write_a_brief(env: Env) -> None:
    await add_user(env, OTHER)
    store, brief_id = AgentBriefStore(env.rt), await _brief(env)
    calls = (
        store.context(OTHER, brief_id),
        store.save_resource(OTHER, "s", brief_id, VIEW),
        store.save_advice(OTHER, "s", brief_id, SENTENCES),
    )
    for call in calls:
        with pytest.raises(AppError) as caught:
            await call
        assert caught.value.code == "brief_not_found" and caught.value.status_code == 404
    [row] = await briefs(env)
    assert row.resource is None and row.advice is None and row.advice_status == "pending"


async def test_unknown_brief_is_not_found(env: Env) -> None:
    with pytest.raises(AppError) as caught:
        await AgentBriefStore(env.rt).context(env.user_id, "inconnu")
    assert caught.value.code == "brief_not_found"
