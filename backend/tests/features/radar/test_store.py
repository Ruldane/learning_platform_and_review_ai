"""Le port du radar sur la vraie base (`AgentRadarStore`, D159, D160) : lecture idempotente et
plafonnée (60), sites bloqués et domaines exclus comptés à part, lectures simultanées sans perte,
extractions idempotentes, repères de page libres (`p12`), contexte relu à chaque passage."""

import asyncio

import pytest
from pydantic import ValidationError

from app.agents.tools.radar_port import MAX_READS
from app.agents.tools.radar_schema import RadarFinding, RadarItem
from app.core.errors import AppError
from app.db.models.daily import RadarRun
from tests.features.radar.support import ME, OTHER, Radar, doc, finding, link


async def test_read_posting_idempotent_and_capped(radar: Radar) -> None:
    run_id = await radar.new_run()
    radar.web.pages[link(1)] = doc(link(1))
    first = await radar.store.read_posting(ME, "s", run_id, link(1))
    # Le même lien, même écrit autrement (suivi de campagne, barre finale) : une seule lecture.
    again = await radar.store.read_posting(ME, "s", run_id, link(1) + "/?utm_source=x")
    assert again == first and first.ref == "p1" and first.url == link(1) and first.status == "ok"
    assert [call[0] for call in radar.web.calls] == [link(1)]
    assert (await radar.row(run_id)).read_count == 1
    await radar.read(run_id, MAX_READS - 1, start=2)
    assert (await radar.row(run_id)).read_count == MAX_READS
    radar.web.pages[link(999)] = doc(link(999))
    with pytest.raises(AppError) as refused:
        await radar.store.read_posting(ME, "s", run_id, link(999))  # la 61e
    assert refused.value.code == "radar_read_limit"
    # Une page déjà lue reste rendue sans erreur, même au plafond.
    assert (await radar.store.read_posting(ME, "s", run_id, link(1))).ref == "p1"


async def test_excluded_domain_counted_blocked(radar: Radar) -> None:
    run_id = await radar.new_run()
    excluded = "https://www.linkedin.com/jobs/view/1"
    page = await radar.store.read_posting(ME, "s", run_id, excluded)
    assert page.status == "unreadable" and page.domain == "linkedin.com" and page.text == ""
    assert radar.web.calls == []  # un domaine exclu n'est jamais lu
    row = await radar.row(run_id)
    assert (row.read_count, row.blocked_count) == (0, 1)
    assert row.blocked_domains == {"linkedin.com": 1}


async def test_blocked_site_counted_by_domain(radar: Radar) -> None:
    run_id = await radar.new_run()
    for number in (1, 2, 3):  # le lecteur factice ne connaît pas ces pages : illisibles
        page = await radar.store.read_posting(ME, "s", run_id, link(number, "ferme.example.org"))
        assert page.status == "unreadable" and page.ref == f"p{number}"
    await radar.read(run_id, 1)
    row = await radar.row(run_id)
    assert row.blocked_domains == {"ferme.example.org": 3}
    assert (row.read_count, row.blocked_count) == (1, 3)


async def test_refused_link_is_an_unreadable_page_not_an_error(radar: Radar) -> None:
    run_id = await radar.new_run()
    for url in ("ftp://jobs.example.org/x", "https://user:pw@jobs.example.org/x"):
        page = await radar.store.read_posting(ME, "s", run_id, url)
        assert page.status == "unreadable"
    assert (await radar.row(run_id)).blocked_count == 2


async def test_simultaneous_reads_lose_nothing(radar: Radar) -> None:
    run_id = await radar.new_run()
    for number in range(5):
        radar.web.pages[link(number)] = doc(link(number))
    pages = await asyncio.gather(
        *[radar.store.read_posting(ME, "s", run_id, link(n)) for n in range(5)]
    )
    assert sorted(page.ref for page in pages) == ["p1", "p2", "p3", "p4", "p5"]
    row = await radar.row(run_id)
    assert row.read_count == 5 and len(row.postings) == 5
    # Deux lectures simultanées du même lien : une seule entrée.
    twin = await asyncio.gather(*[radar.store.read_posting(ME, "s", run_id, link(50))] * 2)
    assert twin[0].ref == twin[1].ref
    assert len((await radar.row(run_id)).postings) == 6


async def test_context_reflects_the_run_each_time(radar: Radar) -> None:
    run_id = await radar.new_run()
    empty = await radar.store.context(ME, run_id)
    assert (empty.role, empty.zone, empty.read, empty.attempts) == ("Ingénieur IA", "Lyon", [], 0)
    assert empty.languages == ("fr", "en")
    await radar.read(run_id, 3)
    await radar.store.read_posting(ME, "s", run_id, link(9, "ferme.example.org"))
    await radar.store.save_extraction(ME, "s", run_id, [finding("p1", "Python")], ["p2"])
    ctx = await radar.store.context(ME, run_id)
    assert [(p.ref, p.status) for p in ctx.read] == [
        ("p1", "ok"),
        ("p2", "ok"),
        ("p3", "ok"),
        ("p4", "unreadable"),
    ]
    assert ctx.extracted == frozenset({"p1", "p2"}) and ctx.attempts == 4
    assert ctx.read[0].text.startswith("Offre fictive")


async def test_other_user_cannot_see_or_write_a_run(radar: Radar) -> None:
    run_id = await radar.new_run()
    for call in (
        radar.store.context(OTHER, run_id),
        radar.store.read_posting(OTHER, "s", run_id, link(1)),
        radar.store.finalize(OTHER, "s", run_id),
    ):
        with pytest.raises(AppError) as missing:
            await call
        assert missing.value.code == "radar_run_not_found"


async def test_extraction_is_idempotent_and_page_refs_are_free(radar: Radar) -> None:
    """`p12` (plus de cinq pages) est un repère de page valable : l'adaptateur ne revalide pas
    un repère de lot (`p1` à `p5`)."""
    run_id = await radar.new_run()
    await radar.read(run_id, 12)
    items = [finding("p12", "Python"), finding("p7", "Rust", is_job_posting=False)]
    await radar.store.save_extraction(ME, "s", run_id, items, ["p3"])
    # Rejeu avec d'autres compétences : rien ne change (la première extraction gagne).
    await radar.store.save_extraction(ME, "s", run_id, [finding("p12", "Go")], ["p12", "p7", "p3"])
    row = await radar.row(run_id)
    by_ref = {entry["ref"]: entry for entry in row.postings}
    assert by_ref["p12"]["skills"] == [{"name": "Python", "required": True}]
    assert by_ref["p7"]["read"] == "not_posting" and by_ref["p3"]["read"] == "extract_failed"
    assert (row.not_postings, row.analyzed) == (1, 1)


def test_finding_keeps_page_refs_that_a_batch_item_refuses() -> None:
    assert RadarFinding.model_validate({"ref": "p12", "is_job_posting": False}).ref == "p12"
    assert RadarFinding.model_validate({"ref": "r1", "is_job_posting": False}).ref == "r1"
    with pytest.raises(ValidationError):
        RadarItem.model_validate({"ref": "p12", "is_job_posting": False})
    with pytest.raises(ValidationError):
        RadarFinding.model_validate({"ref": "", "is_job_posting": False})
    again = RadarFinding.model_validate(finding("p12", "Python").model_dump())
    assert again.ref == "p12"  # une relecture de validation ne casse pas


async def test_salary_is_checked_again_against_the_stored_text(radar: Radar) -> None:
    run_id = await radar.new_run()
    await radar.read(run_id, 2)  # le texte contient « 45 000 »
    await radar.store.save_extraction(
        ME,
        "s",
        run_id,
        [finding("p1", "Python", salary="45 000 euros"), finding("p2", "Python", salary="60 000")],
        [],
    )
    by_ref = {entry["ref"]: entry for entry in (await radar.row(run_id)).postings}
    assert by_ref["p1"]["salary"] == "45 000 euros" and by_ref["p2"]["salary"] is None


async def test_fail_records_the_code_once(radar: Radar) -> None:
    run_id = await radar.new_run()
    await radar.store.fail(ME, "s", run_id, "search_unavailable")
    await radar.store.fail(ME, "s", run_id, "autre")  # un relevé fini ne change plus
    row: RadarRun = await radar.row(run_id)
    assert (row.status, row.error_code) == ("failed", "search_unavailable")
    assert row.finished_at is not None


async def test_save_candidates_records_the_counts(radar: Radar) -> None:
    run_id = await radar.new_run()
    await radar.store.save_candidates(ME, "s", run_id, 5, [link(1), link(2)])
    row = await radar.row(run_id)
    assert (row.queries, row.candidates) == (5, 2)
