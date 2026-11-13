"""Contrôle de fin de phase 5 (étude, puis « tout »), joué de bout en bout contre l'application
réelle (lifespan, moteur, features) : un programme validé semé avec ses leçons prêtes, le Tuteur,
l'Examinateur, le Stratège et l'Archiviste scriptés (`study_script`), les fournisseurs factices, le
planificateur appelé directement. Aucun réseau ni LLM réel ; la santé est remplacée par une réponse
OK."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

import scripts.check_phase4 as check_phase4
import scripts.check_phase5 as check
from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.models.program import Task
from app.db.models.study import Flashcard
from app.features.health.router import get_health_service
from app.main import create_app
from scripts.check_phase5 import ALL_STEPS, ETUDE_STEPS, CheckFailed, run_check
from tests.e2e.scripted_models import ScriptedModels
from tests.e2e.server import healthy_service
from tests.e2e.study_script import study_scripts
from tests.features.study.conftest import DATES, Seeded, seed
from tests.scripts.phase4_fakes import api
from tests.scripts.phase5_support import (
    freeze_weekly_clock,
    readable_page,
    rebase_program,
    weekly_scheduler,
)

ZONE = ZoneInfo("Europe/Paris")


@pytest.fixture
def models() -> ScriptedModels:
    return ScriptedModels(study_scripts())


@pytest.fixture
def app(
    settings: Settings,
    db_engine: AsyncEngine,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    models: ScriptedModels,
) -> FastAPI:
    """L'application sur les modèles scriptés de l'étude, la santé sans sonde."""
    built = create_app(
        settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
        chat_models=models,
    )
    built.dependency_overrides[get_health_service] = healthy_service
    return built


@pytest.fixture
async def seeded_program(client: httpx.AsyncClient, app: FastAPI) -> Seeded:
    """Programme validé de deux semaines, leçons prêtes ; les tâches du premier module sont dues
    aujourd'hui (une en retard), et l'horloge de l'étude est la vraie."""
    s = await seed(app, recording=False)
    today = datetime.now(ZONE).date()
    s.rt.now = lambda: datetime.now(UTC)
    async with s.rt.session_factory() as db:
        for title in DATES:
            late = timedelta(days=1) if title == "Lire le chapitre 1" else timedelta()
            await db.execute(
                update(Task)
                .where(Task.program_id == s.program_id, Task.title == title)
                .values(planned_date=today - late)
            )
        await db.commit()
    return s


async def _add_due_card(s: Seeded) -> None:
    """Une fiche d'un autre jour, due aujourd'hui : la file du jour n'est pas vide."""
    async with s.rt.session_factory() as db:
        db.add(
            Flashcard(
                user_id=s.user_id,
                front="Recto ancien",
                back="Verso ancien",
                front_hash="a" * 64,
                source="quiz",
                due_date=datetime.now(ZONE).date(),
            )
        )
        await db.commit()


async def _cards(s: Seeded) -> list[Flashcard]:
    async with s.rt.session_factory() as db:
        found = await db.execute(select(Flashcard))
        return list(found.scalars())


@pytest.mark.timeout(300)
async def test_check_etude_runs_against_the_app(
    client: httpx.AsyncClient, seeded_program: Seeded, models: ScriptedModels
) -> None:
    await _add_due_card(seeded_program)

    steps = await run_check(client, part="etude", timeout_s=240)

    assert steps == ["santé", "programme", "session", "bilan de session", "quiz", "fiches"]
    assert steps == list(ETUDE_STEPS)
    assert models.served["tutor"] > 0
    assert models.served["examiner"] == 2  # le quiz, puis la notation
    tomorrow = datetime.now(ZONE).date() + timedelta(days=1)
    cards = await _cards(seeded_program)
    assert len(cards) >= 4  # l'ancienne, celles de la session et celles du quiz
    assert {c.due_date for c in cards} == {tomorrow}  # l'ancienne, ratée, revient demain aussi


@pytest.mark.timeout(300)
async def test_check_etude_without_a_due_card(
    client: httpx.AsyncClient, seeded_program: Seeded
) -> None:
    steps = await run_check(client, part="etude", timeout_s=240)

    assert steps == list(ETUDE_STEPS)
    tomorrow = datetime.now(ZONE).date() + timedelta(days=1)
    assert {c.due_date for c in await _cards(seeded_program)} == {tomorrow}


@pytest.mark.timeout(300)
async def test_check_all_runs_against_the_app(
    client: httpx.AsyncClient,
    app: FastAPI,
    seeded_program: Seeded,
    models: ScriptedModels,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _add_due_card(seeded_program)
    monday = await rebase_program(seeded_program)
    readable_page(memory_providers)
    sunday = freeze_weekly_clock(monkeypatch, monday)
    scheduler = asyncio.create_task(weekly_scheduler(client, app, sunday))
    try:
        steps = await run_check(client, part="tout", timeout_s=240)
        await asyncio.wait_for(scheduler, 5)
    finally:
        scheduler.cancel()

    assert steps == list(ALL_STEPS)
    assert steps == [
        "santé", "programme", "carte avant", "session", "bilan de session", "quiz", "fiches",
        "carte après", "replanification", "capture", "bilan hebdomadaire", "journal",
    ]  # fmt: skip
    assert models.served["strategist"] >= 1  # la semaine de 5 heures (le bilan est annulé)
    assert models.served["archivist"] == 2  # le lien lisible, puis le texte collé
    settings = (await client.get("/api/v1/settings")).json()
    assert settings["weekly_review"] == {"day": "sunday", "time": "18:00"}  # remis comme avant
    program_id = seeded_program.program_id
    program = (await client.get(f"/api/v1/programs/{program_id}")).json()
    assert program["version"] == 2  # la proposition acceptée
    replans = (await client.get("/api/v1/sessions", params={"graph": "replan"})).json()
    assert len(replans) == 2  # la semaine de 5 heures, puis le bilan
    assert {r["subject_id"] for r in replans} == {program_id}
    assert "completed" in {r["status"] for r in replans}  # la proposition acceptée


@pytest.mark.timeout(600)
async def test_check_all_can_be_rerun_on_the_same_base(
    client: httpx.AsyncClient,
    app: FastAPI,
    seeded_program: Seeded,
    models: ScriptedModels,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trois passages de suite sur la même base : le quiz du module 1 rate, puis attend son nouvel
    essai (J+2) : le deuxième passage prend le module 2, le troisième ne trouve plus de quiz libre
    et vérifie le blocage. La replanification, le bilan et le journal se rejouent sans erreur."""
    await _add_due_card(seeded_program)
    monday = await rebase_program(seeded_program)
    readable_page(memory_providers)
    scheduler = asyncio.create_task(
        weekly_scheduler(client, app, freeze_weekly_clock(monkeypatch, monday))
    )
    try:
        first = await run_check(client, part="tout", timeout_s=240)
        await asyncio.wait_for(scheduler, 5)
        served = models.served["examiner"]
        second = await run_check(client, part="tout", timeout_s=240)
        assert models.served["examiner"] == served + 2  # un quiz et sa notation : le module 2
        third = await run_check(client, part="tout", timeout_s=240)
    finally:
        scheduler.cancel()

    assert first == second == third == list(ALL_STEPS)
    assert models.served["examiner"] == served + 2  # le troisième passage ne note rien
    settings = (await client.get("/api/v1/settings")).json()
    assert settings["weekly_review"] == {"day": "sunday", "time": "18:00"}


async def test_check_fails_without_a_validated_program(client: httpx.AsyncClient) -> None:
    with pytest.raises(CheckFailed, match="check_phase4") as caught:
        await run_check(client, part="etude", timeout_s=5)

    assert caught.value.step == "programme"


async def test_check_stops_at_the_first_failed_step() -> None:
    def degraded(request: httpx.Request) -> httpx.Response:
        checks = {"db": {"ok": True}, "llm": {"ok": False, "detail": "Clé absente"}}
        return httpx.Response(200, json={"status": "degraded", "checks": checks})

    transport = httpx.MockTransport(degraded)
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        with pytest.raises(CheckFailed) as caught:
            await run_check(client, part="etude", timeout_s=5)

    assert caught.value.step == "santé"
    assert "llm" in str(caught.value)


async def test_with_phase4_runs_the_phase_four_check_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def phase4(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        calls.append("phase4")
        return []

    monkeypatch.setattr(check_phase4, "run_check", phase4)
    routes: dict[str, Any] = {"/health": {"checks": {}}}
    async with api(routes) as client:
        with pytest.raises(CheckFailed) as caught:
            await run_check(client, part="etude", with_phase4=True, timeout_s=5)

    assert calls == ["phase4"]  # puis la phase 5 commence : la santé échoue ici
    assert caught.value.step == "santé"


def test_main_exits_with_one_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        raise CheckFailed("session", "Session d'étude interrupted.")

    monkeypatch.setattr(check, "run_check", failing)
    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "etude"])
    assert exited.value.code == 1


def test_main_passes_its_options_and_exits_with_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    async def passing(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        seen.update(kwargs)
        return list(ETUDE_STEPS)

    monkeypatch.setattr(check, "run_check", passing)
    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "etude", "--with-phase4"])

    assert exited.value.code == 0
    assert seen == {"part": "etude", "with_phase4": True, "timeout_s": 3600.0}


def test_main_runs_every_step_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    async def passing(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        seen.update(kwargs)
        return list(ALL_STEPS)

    monkeypatch.setattr(check, "run_check", passing)
    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--timeout", "3600"])

    assert exited.value.code == 0
    assert seen == {"part": "tout", "with_phase4": False, "timeout_s": 3600.0}
