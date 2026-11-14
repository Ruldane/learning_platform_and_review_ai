"""Comparaison de la carte à une offre (D123) : `GET /skills/compare?target=posting&posting_id=…`
rend la même forme que `target=goal` : une ligne par compétence apprenable de l'offre (nom
rattaché au référentiel, sinon celui du besoin), cible `valide`. `posting_id` est obligatoire
(422 sans valeur) ; une offre d'une autre ou absente : 404 ; pas encore analysée : 404
`no_compare_target`."""

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI

from app.core.skills import evidence
from app.features.skills.service import SkillsService
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import analyzed_posting
from tests.features.skills.support import API
from tests.support.gap import LEVELS, SKILLS

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)
PERMIT = {"name": "Permis B", "required": False, "domain": None, "learnable": False}


async def _levels(app: FastAPI) -> None:
    async with app.state.session_factory() as db:
        skills = SkillsService(db, app.state.local_user_id)
        for name, level in LEVELS.items():
            if level is not None:
                await skills.raise_levels([name], level, evidence("quiz", name, name, NOW))
        await db.commit()


def _skills() -> list[dict[str, Any]]:
    needs = [
        {"name": name, "required": required, "domain": None, "learnable": learnable}
        for name, required, learnable in SKILLS
    ]
    return [*needs, PERMIT]


async def test_compare_with_posting(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    await _levels(app)
    posting_id = await analyzed_posting(client, app, skills=_skills())
    params = {"target": "posting", "posting_id": posting_id}
    r = await client.get(f"{API}/skills/compare", params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_label"] == "AI Product Engineer — Société Fictive"
    rows = {row["name"]: (row["mine"], row["target"], row["gap"]) for row in body["rows"]}
    assert list(rows) == [
        "Python", "LangGraph", "Génération augmentée par recherche", "Recherche vectorielle",
        "Agents LLM", "Évaluation de RAG", "Développement logiciel", "Docker",
        "Intégration continue", "Anglais professionnel",
    ]  # fmt: skip
    assert rows["Python"] == ("valide", "valide", 0)
    assert rows["Recherche vectorielle"] == ("prouve", "valide", -1)
    assert rows["Docker"] == ("declare", "valide", 2)
    assert rows["LangGraph"] == (None, "valide", 3)
    assert body["coverage"] == 50  # 5 compétences atteintes sur 10 ; le permis n'en est pas
    goal_shape = set(body) == {"target_label", "coverage", "rows"}
    assert goal_shape and r.headers["cache-control"] == "no-store"


async def test_compare_posting_requires_id(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    r = await client.get(f"{API}/skills/compare", params={"target": "posting"})
    assert r.status_code == 422 and r.json()["error"] == {
        "code": "posting_id_required",
        "message": "Choisis l'offre à comparer.",
        "details": {"fields": ["posting_id"]},
    }
    secret = "offre-secrete-" + "x" * 80
    r = await client.get(
        f"{API}/skills/compare", params={"target": "posting", "posting_id": secret}
    )
    assert r.status_code == 422 and "secrete" not in r.text
    unknown = {"target": "posting", "posting_id": "inconnue"}
    r = await client.get(f"{API}/skills/compare", params=unknown)
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")
    pending = await client.post(f"{API}/postings", json={"text": POSTING_TEXT})
    params = {"target": "posting", "posting_id": pending.json()["posting"]["id"]}
    r = await client.get(f"{API}/skills/compare", params=params)
    assert (r.status_code, r.json()["error"]["code"]) == (404, "no_compare_target")
