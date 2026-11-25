"""Offres d'une compétence (D123) : le détail d'une compétence liste les offres prêtes dont
l'analyse la cite (nom du besoin, rattachement au référentiel ou synonyme), les plus récentes
d'abord, dix au plus ; une offre encore en analyse n'y est pas."""

import httpx
from fastapi import FastAPI

from app.core.skills import normalize_skill_name
from app.features.gap.service.links import postings_citing
from app.features.skills.repository import SkillRepository
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import analyzed_posting
from tests.features.skills.support import API, add_skill


async def _skill_id(app: FastAPI, name: str) -> str:
    async with app.state.session_factory() as db:
        found = await SkillRepository(db, app.state.local_user_id).by_norm(
            [normalize_skill_name(name)]
        )
    return found[normalize_skill_name(name)].id


async def _postings(client: httpx.AsyncClient, skill_id: str) -> list[dict[str, str]]:
    r = await client.get(f"{API}/skills/{skill_id}")
    assert r.status_code == 200, r.text
    postings: list[dict[str, str]] = r.json()["postings"]
    return postings


async def test_skill_detail_lists_postings(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    factory, me = app.state.session_factory, app.state.local_user_id
    rag = await add_skill(factory, me, "Génération augmentée par recherche", level="validated")
    agents = await add_skill(factory, me, "Graphes d'agents", synonyms=["LangGraph"])
    kubernetes = await add_skill(factory, me, "Kubernetes", level="declared")
    older = await analyzed_posting(client, app)
    newer = await analyzed_posting(
        client, app, f"{POSTING_TEXT}\nPoste basé à Lyon.", title="Lead IA"
    )
    pending = await client.post(f"{API}/postings", json={"text": f"{POSTING_TEXT}\nAutre."})
    assert pending.status_code == 201  # en analyse : jamais listée
    expected = [
        {"id": newer, "title": "Lead IA", "url": f"/career/postings/{newer}"},
        {"id": older, "title": "AI Product Engineer", "url": f"/career/postings/{older}"},
    ]
    assert await _postings(client, await _skill_id(app, "LangGraph")) == expected  # besoin
    assert await _postings(client, rag) == expected  # rattachement de « RAG »
    assert await _postings(client, agents) == expected  # synonyme
    assert await _postings(client, kubernetes) == []
    async with factory() as db:
        assert [p.posting_id for p in await postings_citing(db, me, ["LangGraph"], 1)] == [newer]
