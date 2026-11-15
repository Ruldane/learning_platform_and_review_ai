"""Branche `company_brief` du kit (Éclaireur, mode `dossier`, D142) : dossier repris s'il est
récent, sinon recherche, quatre lectures au plus, citations vérifiées par le code."""

from app.agents.tools.kit_schema import CompanyDossier, SourceRef
from app.agents.tools.web_port import PageRead
from tests.agents.graphs.kit_support import MakeKit, dossier, dossier_data, prompts, writers
from tests.agents.graphs.review_support import FakeWeb
from tests.support.kit import COMPANY, FakeKitStore

NO_SOURCE = "Aucune source lisible : dossier non produit."


def fresh_dossier() -> CompanyDossier:
    return CompanyDossier.model_validate(dossier_data(activity="Reprise du dossier [1]."))


async def test_dossier_reused_when_fresh(
    kit_runner: MakeKit, kit_store: FakeKitStore, kit_web: FakeWeb
) -> None:
    kit_store.update(
        company_dossier=fresh_dossier(),
        company_dossier_sources=[SourceRef(url="https://exemple.org/a", title="Page A")],
    )
    run = await kit_runner()
    await run.wait_status("completed")
    assert prompts(run.models, "dossier") == [] and kit_web.searches == [] and kit_web.reads == []
    assert kit_store.dossiers == []  # rien n'est réécrit dans `companies`
    row = kit_store.piece("company_brief")
    assert row.status == "ready" and row.meta == {"sources": 1, "reused": True}
    assert "Reprise du dossier [1]." in row.content
    assert "[1] Page A — https://exemple.org/a" in row.content


async def test_dossier_researched_and_rendered_with_sources(
    kit_runner: MakeKit, kit_store: FakeKitStore, kit_web: FakeWeb
) -> None:
    run = await kit_runner()
    await run.wait_status("completed")
    assert len(kit_web.searches) == 2 and len(kit_web.reads) == 4  # quatre lectures au plus
    row = kit_store.piece("company_brief")
    assert row.status == "ready" and row.meta == {"sources": 4, "emptied": 0, "dropped": 0}
    for heading in ("# Dossier : Société Fictive", "## Activité", "## Actualité", "## Sources"):
        assert heading in row.content
    assert "2026-10-01 : Levée de fonds annoncée [2]" in row.content
    assert "1. Question a sur l'équipe ?" in row.content
    [(company, saved, sources)] = kit_store.dossiers
    assert (
        company == COMPANY and len(sources) == 4 and saved.questions == dossier_data()["questions"]
    )


async def test_dossier_reads_four_pages_at_most(kit_runner: MakeKit, kit_web: FakeWeb) -> None:
    kit_web.urls = [f"https://site{n}.example.org/societe" for n in range(9)]
    run = await kit_runner()
    await run.wait_status("completed")
    assert len(kit_web.reads) == 4


async def test_dossier_citation_without_source_removed(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    reply = dossier(
        activity="Éditeur de logiciels [1] [7].",
        product="Des produits variés, sans aucune source.",
        stack=["Python [1, 9]", "Rust"],
        news=[
            {"text": "Ancienne levée de fonds [2]", "date": "2025-01-10"},
            {"text": "Annonce sans date [2]", "date": None},
            {"text": "Annonce citant une page non lue [8]", "date": "2026-10-20"},
            {"text": "Nouveau bureau ouvert [3]", "date": "2026-11-02"},
        ],
        watch_points=["Rythme soutenu [4]", "Rumeur sans source"],
    )
    run = await kit_runner(writers(dossier=[reply]))
    await run.wait_status("completed")
    row = kit_store.piece("company_brief")
    assert "[7]" not in row.content and "[9]" not in row.content and "[8]" not in row.content
    assert "Éditeur de logiciels [1]" in row.content and "- Python [1]" in row.content
    assert "Rust" not in row.content and "Rumeur" not in row.content
    assert "Ancienne levée" not in row.content and "sans date" not in row.content
    assert "non lue" not in row.content and "2026-11-02 : Nouveau bureau ouvert [3]" in row.content
    assert "Des produits variés" not in row.content  # aucune affirmation sans source lue
    assert "## Produit\nNon trouvé dans les sources lues." in row.content
    assert row.status == "to_check" and row.meta["emptied"] == 1 and row.meta["dropped"] == 5


async def test_dossier_without_readable_source_is_not_produced(
    kit_runner: MakeKit, kit_store: FakeKitStore, kit_web: FakeWeb
) -> None:
    kit_web.urls = []
    run = await kit_runner()
    await run.wait_status("completed")
    row = kit_store.piece("company_brief")
    assert (row.status, row.content) == ("to_check", NO_SOURCE)
    assert prompts(run.models, "dossier") == [] and kit_store.dossiers == []


async def test_dossier_with_no_sourced_text_is_not_produced(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    unsourced = dossier(
        activity="Sans source.", product="Sans source.", culture="Sans source.",
        interview_process="Sans source.", stack=[], news=[], watch_points=[],
    )  # fmt: skip
    run = await kit_runner(writers(dossier=[unsourced]))
    await run.wait_status("completed")
    row = kit_store.piece("company_brief")
    assert (row.status, row.content) == ("to_check", NO_SOURCE) and kit_store.dossiers == []


async def test_dossier_search_failure_fails_only_that_piece(
    kit_runner: MakeKit, kit_store: FakeKitStore, kit_web: FakeWeb
) -> None:
    from app.core.errors import AppError

    async def broken(*_: object, **__: object) -> None:
        raise AppError("search_unavailable", "Aucun moteur de recherche disponible.", 503)

    kit_web.search = broken  # type: ignore[method-assign]
    run = await kit_runner()
    await run.wait_status("completed")
    row = kit_store.piece("company_brief")
    assert row.status == "failed" and row.meta["error"] == "Aucun moteur de recherche disponible."
    assert {r.status for k, r in kit_store.rows.items() if k[1] != "company_brief"} == {"ready"}


async def test_unknown_company_skips_the_dossier(
    kit_runner: MakeKit, kit_store: FakeKitStore, kit_web: FakeWeb
) -> None:
    kit_store.update(company=" ")
    run = await kit_runner()
    await run.wait_status("completed")
    row = kit_store.piece("company_brief")
    assert row.status == "to_check" and "Entreprise inconnue" in row.content
    assert kit_web.searches == []


async def test_dossier_news_citing_an_old_page_is_dropped(
    kit_runner: MakeKit, kit_store: FakeKitStore, kit_web: FakeWeb
) -> None:
    from dataclasses import replace

    original = kit_web.read

    async def dated(user_id: str, session_id: str, url: str) -> PageRead:
        page = await original(user_id, session_id, url)
        return replace(page, date="2025-01-10" if url == kit_web.urls[1] else None)

    kit_web.read = dated  # type: ignore[method-assign]
    news = [
        {"text": "Annonce récente [1]", "date": "2026-11-01"},
        {"text": "Annonce d'une page ancienne [2]", "date": "2026-11-01"},
    ]
    run = await kit_runner(writers(dossier=[dossier(news=news)]))
    await run.wait_status("completed")
    content = kit_store.piece("company_brief").content
    assert "Annonce récente [1]" in content
    assert "page ancienne" not in content
