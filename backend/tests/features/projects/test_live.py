"""Les projets sur le vrai moteur d'agents (D165, D166) : le vrai lanceur, le vrai port
(`AgentProjectStore`), les parcours `project_brief` et `project_review` sur des modèles scriptés.
Aucun réseau ni LLM réel. Prouve le branchement de bout en bout : énoncé rangé, rendu évalué,
validation (compétences `prouve`, brouillons, fil d'activité), échec d'une session (le projet est
rendu à January), trois essais de l'énoncé puis « Réessayer »."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.features.projects.service.briefs import ensure_project_briefs
from app.main import create_app
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.project_support import (
    BRIEF_ASK,
    DRAFTS_ASK,
    EVALUATE_ASK,
    all_met,
    brief_json,
    drafts_json,
    project_models,
)
from tests.features.lessons.conftest import count_open_sessions
from tests.features.projects.support import API, WEEK_1
from tests.features.study.conftest import SKILLS, seed
from tests.support.projects import DESCRIPTION, REPO_URL


@dataclass
class Live:
    app: FastAPI
    client: httpx.AsyncClient
    models: CouncilModels

    async def idle(self) -> None:
        """Attend la fin de toutes les sessions de projets."""
        for _ in range(300):
            opened = [
                await count_open_sessions(self.app.state.session_factory, graph)
                for graph in ("project_brief", "project_review")
            ]
            if not any(opened):
                return
            await asyncio.sleep(0.1)
        raise AssertionError("des sessions de projets restent ouvertes")

    async def project(self, project_id: str) -> dict[str, Any]:
        await self.idle()
        body: dict[str, Any] = (await self.client.get(f"{API}/{project_id}")).json()
        return body


async def start(
    app_models: CouncilModels,
    settings: Settings,
    memory: MemoryProviders,
    research: ResearchProviders,
    publishing: PublishingProviders,
) -> AsyncIterator[Live]:
    app = create_app(
        settings,
        memory_providers=memory,
        research_providers=research,
        publishing_providers=publishing,
        chat_models=app_models,
    )
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await seed(app, recording=False)
            app.state.daily.projects.now = lambda: WEEK_1
            yield Live(app, client, app_models)


@pytest.fixture
async def live(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> AsyncIterator[Live]:
    models = project_models(brief=[brief_json()], evaluation=[all_met(3)], drafts=[drafts_json()])
    async for found in start(
        models, settings, memory_providers, research_providers, publishing_providers
    ):
        yield found


async def _created(live: Live) -> str:
    assert await ensure_project_briefs(live.app.state.daily.projects, WEEK_1) == 1
    [row] = (await live.client.get(API)).json()
    return str(row["id"])


async def test_brief_then_review_run_through_the_real_engine(live: Live) -> None:
    pid = await _created(live)
    shown = await live.project(pid)
    assert shown["status"] == "todo" and shown["title"] == "Une API de suivi de lecture"
    assert len(shown["brief"]["criteria"]) == 3 and shown["session_id"] is None
    sent = await live.client.post(
        f"{API}/{pid}/submit", data={"repo_url": REPO_URL, "description": DESCRIPTION}
    )
    assert sent.status_code == 202
    done = await live.project(pid)
    assert done["status"] == "validated" and done["validated_at"] and done["session_id"] is None
    assert [c["met"] for c in done["evaluation"]["results"]] == [True, True, True]
    assert [d["kind"] for d in done["drafts"]] == [
        "cv_line",
        "profile_entry",
        "linkedin_post",
        "readme_plan",
    ]
    assert done["profile_version"] is None
    levels = (await live.client.get("/api/v1/skills/graph")).json()
    assert {SKILLS[0]} <= {n["name"] for n in levels["nodes"] if n["level"] == "prouve"}
    feed = (await live.client.get("/api/v1/activity")).json()
    titles = [i["title"] for i in feed["items"] if i["kind"] == "project"]
    assert titles == ["Projet validé : Une API de suivi de lecture"]
    journal = (await live.client.get("/api/v1/journal", params={"kind": "project"})).json()
    assert len(journal["entries"]) == 1


@pytest.fixture
async def failing(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> AsyncIterator[Live]:
    models = project_models(brief=[brief_json()], evaluation=["pas du json"] * 3)
    models.when("practitioner", EVALUATE_ASK, all_met(3))
    models.when("practitioner", DRAFTS_ASK, drafts_json())
    async for found in start(
        models, settings, memory_providers, research_providers, publishing_providers
    ):
        yield found


async def test_a_failed_review_session_gives_the_project_back_for_a_new_try(
    failing: Live,
) -> None:
    pid = await _created(failing)
    assert (await failing.project(pid))["status"] == "todo"
    first = await failing.client.post(f"{API}/{pid}/submit", data={"description": DESCRIPTION})
    assert first.status_code == 202
    back = await failing.project(pid)  # l'évaluation a échoué : rien n'est rangé
    assert back["status"] == "todo" and back["evaluation"] is None and back["drafts"] == []
    assert len(back["submissions"]) == 1 and back["session_id"] is None
    second = await failing.client.post(f"{API}/{pid}/submit", data={"description": DESCRIPTION})
    assert second.status_code == 202 and second.json()["session_id"] != first.json()["session_id"]
    assert (await failing.project(pid))["status"] == "validated"


@pytest.fixture
async def unwritten(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> AsyncIterator[Live]:
    models = project_models()
    models.when("practitioner", BRIEF_ASK, *(["pas du json"] * 9), brief_json())
    async for found in start(
        models, settings, memory_providers, research_providers, publishing_providers
    ):
        yield found


async def test_three_failed_briefs_then_retry_route_writes_it(unwritten: Live) -> None:
    pid = await _created(unwritten)
    rt = unwritten.app.state.daily.projects
    assert (await unwritten.project(pid))["status"] == "brief_pending"  # essai 1 : sans énoncé
    for _ in range(2):  # essais 2 et 3, relancés par la tâche
        await ensure_project_briefs(rt, WEEK_1)
        await unwritten.idle()
    await ensure_project_briefs(rt, WEEK_1)
    failed = await unwritten.project(pid)
    assert failed["status"] == "brief_failed" and failed["brief"] is None
    retried = await unwritten.client.post(f"{API}/{pid}/brief")
    assert retried.status_code == 202
    assert (await unwritten.project(pid))["status"] == "todo"
