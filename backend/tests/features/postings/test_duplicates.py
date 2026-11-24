"""Doublons probables et possibles (D122), calculés après l'analyse : même entreprise et titre
proche, ou même entreprise et texte proche (recherche de la mémoire) ; rangés des deux côtés,
dates dans le fuseau de January, retirés par « offres distinctes » ; jamais l'offre elle-même."""

from typing import Any

import pytest

from app.agents.tools.memory_port import MemoryHitView, MemorySearchResult
from app.core.errors import AppError
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.postings.service.agent_store import AgentGapStore
from app.features.postings.service.duplicates import mark_distinct
from scripts.sample_posting import POSTING_TEXT
from tests.features.postings.conftest import ME, add_posting, analysis, fresh
from tests.features.program.support import Factory

OTHER_TEXT = POSTING_TEXT.replace("Lyon", "Grenoble") + "\nPoste ouvert aux profils juniors."


async def _analyzed(store: AgentGapStore, factory: Factory, text: str, **over: Any) -> str:
    posting_id = await add_posting(factory, text=text)
    await store.save_analysis(ME, f"s-{posting_id}", posting_id, analysis(**over))
    return posting_id


@pytest.fixture
def fake_search(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    """`élément de mémoire → score` rendu par la recherche (aucune vectorisation réelle)."""
    scores: dict[str, float] = {}

    async def search(
        self: AgentMemoryGateway, user_id: str, query: str, *, kinds: Any, k: int
    ) -> MemorySearchResult:
        assert kinds == ["posting"] and len(query) <= 500
        hits = [
            MemoryHitView(item_id, f"c-{item_id}", "posting", "t", "x", score, "analyst")
            for item_id, score in scores.items()
        ]
        return MemorySearchResult(hits, "")

    monkeypatch.setattr(AgentMemoryGateway, "search", search)
    return scores


async def test_probable_duplicate_same_company_similar_title(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    first = await _analyzed(store, db_session_factory, POSTING_TEXT)
    second_id = await add_posting(db_session_factory, text=OTHER_TEXT)
    saved = await store.save_analysis(
        ME, "s2", second_id, analysis(title="Product Engineer AI", company="SOCIÉTÉ FICTIVE S.A.S.")
    )
    assert [(h.level, h.posting_id, h.company) for h in saved.duplicates] == [
        ("probable", first, "Société Fictive")
    ]
    assert saved.duplicates[0].created_at.endswith("+01:00")  # heure de Paris en novembre
    # Rangé des deux côtés, et rendu de nouveau au rejeu.
    assert (await fresh(db_session_factory, first)).duplicates == [
        {"level": "probable", "posting_id": second_id, "score": None}
    ]
    replay = await store.save_analysis(ME, "s2", second_id, analysis())
    assert not replay.first and [h.posting_id for h in replay.duplicates] == [first]


async def test_other_company_or_far_title_is_not_probable(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    await _analyzed(store, db_session_factory, POSTING_TEXT)
    other = await add_posting(db_session_factory, text=OTHER_TEXT)
    saved = await store.save_analysis(ME, "s2", other, analysis(company="Autre Société"))
    far = await add_posting(db_session_factory, text=OTHER_TEXT + " Comptabilité.")
    saved_far = await store.save_analysis(ME, "s3", far, analysis(title="Comptable fournisseurs"))
    assert saved.duplicates == [] and saved_far.duplicates == []


async def test_possible_duplicate_by_vector(
    store: AgentGapStore, db_session_factory: Factory, fake_search: dict[str, float]
) -> None:
    first = await _analyzed(store, db_session_factory, POSTING_TEXT, title="Ingénieur IA")
    item = (await fresh(db_session_factory, first)).memory_item_id
    assert item is not None
    fake_search[item] = 0.93
    second = await add_posting(db_session_factory, text=OTHER_TEXT)
    saved = await store.save_analysis(ME, "s2", second, analysis(title="Développeur LLM"))
    assert [(h.level, h.posting_id, h.score) for h in saved.duplicates] == [
        ("possible", first, 0.93)
    ]
    fake_search[item] = 0.85
    third = await add_posting(db_session_factory, text=OTHER_TEXT + " Bis.")
    below = await store.save_analysis(ME, "s3", third, analysis(title="Architecte données"))
    assert below.duplicates == []


async def test_search_down_gives_no_possible_duplicate(
    store: AgentGapStore, db_session_factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def down(*args: Any, **kwargs: Any) -> MemorySearchResult:
        raise AppError("memory_unavailable", "Mémoire indisponible.", 503)

    await _analyzed(store, db_session_factory, POSTING_TEXT, title="Ingénieur IA")
    monkeypatch.setattr(AgentMemoryGateway, "search", down)
    second = await add_posting(db_session_factory, text=OTHER_TEXT)
    saved = await store.save_analysis(ME, "s2", second, analysis(title="Développeur LLM"))
    assert saved.duplicates == [] and saved.first


async def test_distinct_hides_duplicate_both_ways(
    store: AgentGapStore, db_session_factory: Factory
) -> None:
    first = await _analyzed(store, db_session_factory, POSTING_TEXT)
    second = await _analyzed(store, db_session_factory, OTHER_TEXT, title="Product Engineer AI")
    assert (await fresh(db_session_factory, second)).duplicates
    async with db_session_factory() as db:
        await mark_distinct(db, ME, second, first)
        await mark_distinct(db, ME, second, first)  # idempotent
        await db.commit()
    a, b = await fresh(db_session_factory, first), await fresh(db_session_factory, second)
    assert (a.duplicates, b.duplicates) == ([], [])
    assert (a.distinct_from, b.distinct_from) == ([second], [first])
    replay = await store.save_analysis(ME, "s-again", second, analysis())
    assert replay.duplicates == []
