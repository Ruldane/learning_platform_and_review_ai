"""Fin d'un relevé (P6 à P9, D160) : classement, évolution contre le relevé précédent de même poste
et même zone, alertes sur les offres **analysées**, score, enrichissement du référentiel sans
niveau, rapport honnête (lues, bloquées, analysées, pas analysées)."""

from datetime import timedelta

from sqlalchemy import select

from app.db.models.skills import Skill, UserSkill
from app.features.radar.schemas import RadarRunOut
from app.features.radar.service.demand import latest_demand
from app.features.radar.service.views import run_out
from tests.features.radar.support import ME, NOW, OTHER, Radar, finding, link
from tests.features.skills.support import add_goal, add_program, add_skill


def _postings(count: int, python: int, rust: int = 0) -> list[list[str]]:
    """`count` offres : `python` d'entre elles citent Python, `rust` citent Rust."""
    return [
        (["Python"] if n < python else []) + (["Rust"] if n < rust else []) + ["Linux"]
        for n in range(count)
    ]


async def _out(radar: Radar, run_id: str) -> RadarRunOut:
    async with radar.factory() as db:
        return await run_out(db, ME, await radar.row(run_id))


async def test_finalize_ranking_evolution_alerts(radar: Radar) -> None:
    run1 = await radar.analyzed_run(_postings(10, python=4))  # Python 40 %, Linux 100 %
    first = await _out(radar, run1)
    assert first.previous is None and first.status == "done"
    assert [(t.skill, t.share, t.rank) for t in first.ranking] == [
        ("Linux", 1.0, 1),
        ("Python", 0.4, 2),
    ]
    assert all(t.delta_share is None and not t.new for t in first.ranking)  # premier relevé
    radar.rt.now = lambda: NOW + timedelta(days=7)
    run2 = await radar.analyzed_run(_postings(10, python=6, rust=3))
    second = await _out(radar, run2)
    assert second.previous is not None and second.previous.id == run1
    python = next(t for t in second.ranking if t.skill == "Python")
    assert python.delta_share == 20 and python.delta_rank == 0
    rust = next(t for t in second.ranking if t.skill == "Rust")
    assert rust.new and rust.delta_share is None
    # 10 offres analysées, Python 60 %, Linux 100 % : demandées, absentes du programme.
    assert [a.skill for a in second.alerts] == ["Linux", "Python"]
    assert second.alerts[0].message.startswith("Demandée dans 100 %")
    assert second.alerts[1].message == "Demandée dans 60 % des offres, absente de ton programme."


async def test_evolution_compares_the_same_role_and_zone_only(radar: Radar) -> None:
    await radar.analyzed_run(_postings(10, python=4), role="Autre poste")
    radar.rt.now = lambda: NOW + timedelta(days=7)
    other_zone = await radar.analyzed_run(_postings(10, python=4), zone="Paris")
    assert (await _out(radar, other_zone)).previous is None
    radar.rt.now = lambda: NOW + timedelta(days=14)
    same = await radar.analyzed_run(_postings(10, python=4))
    assert (await _out(radar, same)).previous is None  # ni le poste ni la zone des deux premiers


async def test_alerts_count_analyzed_postings_not_the_ones_read(radar: Radar) -> None:
    """15 offres lues mais 8 analysées seulement : pas d'alerte (il en faut 10 analysées)."""
    run_id = await radar.new_run()
    await radar.read(run_id, 15)
    await radar.extract(run_id, [["Python"]] * 8)
    summary = await radar.store.finalize(ME, "s", run_id)
    assert (summary.read_ok, summary.analyzed) == (15, 8)
    out = await _out(radar, run_id)
    assert out.alerts == [] and [t.skill for t in out.ranking] == ["Python"]
    # Avec 10 offres analysées (et 5 lues de plus), l'alerte arrive.
    ten = await radar.new_run(role="Autre")
    await radar.read(ten, 15)
    await radar.extract(ten, [["Python"]] * 10)
    await radar.store.finalize(ME, "s", ten)
    assert [a.skill for a in (await _out(radar, ten)).alerts] == ["Python"]


async def test_skill_in_the_program_or_acquired_gives_no_alert(radar: Radar) -> None:
    goal = await add_goal(radar.factory, ME)
    await add_program(radar.factory, ME, goal, [("Module Python", ["python"])])
    await add_skill(radar.factory, ME, "Linux", "Système", "valide")
    run_id = await radar.analyzed_run(_postings(10, python=10))
    assert (await _out(radar, run_id)).alerts == []  # Python au programme, Linux validé


async def test_synonyms_of_the_catalog_count_as_the_program(radar: Radar) -> None:
    goal = await add_goal(radar.factory, ME)
    await add_program(radar.factory, ME, goal, [("Module GNU", ["gnu linux"])])
    await add_skill(radar.factory, ME, "GNU Linux", "Système", synonyms=["Linux"])
    run_id = await radar.analyzed_run(_postings(10, python=10))
    assert [a.skill for a in (await _out(radar, run_id)).alerts] == ["Python"]


async def test_low_sample_flag(radar: Radar) -> None:
    eighteen = await radar.analyzed_run(_postings(18, python=9))
    out = await _out(radar, eighteen)
    assert out.low_sample and (out.read_count, out.analyzed) == (18, 18)
    radar.rt.now = lambda: NOW + timedelta(days=7)
    thirty = await radar.analyzed_run(_postings(30, python=9), role="Autre")
    assert not (await _out(radar, thirty)).low_sample


async def test_pages_that_are_not_postings_do_not_make_a_sample(radar: Radar) -> None:
    run_id = await radar.new_run()
    await radar.read(run_id, 32)
    items = [finding(f"p{n}", "Python", is_job_posting=n > 3) for n in range(1, 33)]
    await radar.store.save_extraction(ME, "s", run_id, items, [])
    summary = await radar.store.finalize(ME, "s", run_id)
    assert (summary.read_ok, summary.not_postings, summary.analyzed) == (32, 3, 29)
    assert summary.low_sample  # 29 offres lisibles, pas 32


async def test_run_says_how_many_were_read_but_not_analyzed(radar: Radar) -> None:
    """55 offres lues, 50 analysées : l'écart est dit (échec d'extraction, plafond)."""
    run_id = await radar.new_run()
    await radar.read(run_id, 55)
    await radar.extract(run_id, [["Python"]] * 50)
    await radar.store.finalize(ME, "s", run_id)
    out = await _out(radar, run_id)
    assert (out.read_count, out.analyzed, out.not_analyzed, out.not_postings) == (55, 50, 5, 0)
    failed = await radar.new_run(role="Autre")
    await radar.read(failed, 4)
    await radar.store.save_extraction(ME, "s", failed, [finding("p1", "Rust")], ["p2", "p3"])
    await radar.store.finalize(ME, "s", failed)
    other = await _out(radar, failed)
    assert (other.read_count, other.analyzed, other.not_analyzed) == (4, 1, 3)


async def test_enrich_catalog_without_level(radar: Radar) -> None:
    await add_skill(radar.factory, ME, "Python", "Langages", "valide")
    await radar.analyzed_run(_postings(10, python=4, rust=2))  # Linux 100 %, Python 40 %, Rust 20 %
    async with radar.factory() as db:
        names = {
            s.name for s in (await db.execute(select(Skill).where(Skill.user_id == ME))).scalars()
        }
        levels = list(
            (await db.execute(select(UserSkill).where(UserSkill.user_id == ME))).scalars()
        )
    assert names == {"Python", "Linux"}  # ≥ 30 % des offres : Rust (20 %) reste dehors
    assert [(row.level) for row in levels] == ["valide"]  # Linux est au référentiel sans niveau


async def test_offers_have_scores_best_first_and_no_page_text(radar: Radar) -> None:
    await add_skill(radar.factory, ME, "Python", "Langages", "valide")
    run_id = await radar.analyzed_run([["Rust"], ["Python"], ["Python", "Rust"]])
    out = await _out(radar, run_id)
    scores = [offer.score for offer in out.offers]
    assert scores == sorted(scores, reverse=True) and scores[0] > scores[-1]
    assert out.offers[0].url == link(1)  # l'offre qui ne demande que Python
    assert all(offer.title and offer.company == "Société Fictive" for offer in out.offers)
    assert all("text" not in entry for entry in (await radar.row(run_id)).postings)


async def test_finalize_is_idempotent_and_leaves_a_failed_run_alone(radar: Radar) -> None:
    run_id = await radar.new_run()
    await radar.read(run_id, 3)
    await radar.extract(run_id, [["Python"]] * 3)
    first = await radar.store.finalize(ME, "s", run_id)
    row = await radar.row(run_id)
    assert row.status == "done" and row.finished_at == NOW
    radar.rt.now = lambda: NOW + timedelta(hours=1)
    assert await radar.store.finalize(ME, "s", run_id) == first
    assert (await radar.row(run_id)).finished_at == NOW
    dead = await radar.new_run(role="Autre")
    await radar.store.fail(ME, "s", dead, "search_unavailable")
    await radar.store.finalize(ME, "s", dead)
    assert (await radar.row(dead)).status == "failed"


async def test_latest_demand_is_the_share_of_the_latest_done_run(radar: Radar) -> None:
    async with radar.factory() as db:
        assert await latest_demand(db, ME) == {}
    await radar.analyzed_run(_postings(10, python=3))
    running = await radar.new_run(role="En cours")  # un relevé en cours ne compte pas
    assert running
    radar.rt.now = lambda: NOW + timedelta(days=7)
    await radar.analyzed_run(_postings(10, python=6), role="Récent")
    async with radar.factory() as db:
        assert await latest_demand(db, ME) == {"linux": 1.0, "python": 0.6}
        assert await latest_demand(db, OTHER) == {}
