"""Santé et planificateur en mode Google (P12) : plus d'« utilisateur local », `/health` reste
public et le contrôle `llm` n'est jamais un état dégradé permanent."""

import asyncio
import logging
from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.features.health.checks import GOOGLE_MODE_DETAIL, LlmKeysCheck
from app.main import create_app


@pytest.fixture
async def google_app_for_health(
    google_settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> AsyncIterator[FastAPI]:
    app = create_app(
        google_settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app):
        yield app


HEALTH = "/api/v1/health"
MESSAGE = "Google mode: each account's keys are checked in its settings."


def llm_check(app: FastAPI) -> LlmKeysCheck:
    (check,) = [c for c in app.state.providers.health_checks if c.name == "llm"]
    assert isinstance(check, LlmKeysCheck)
    return check


async def test_health_llm_ok_in_google_mode(google_app_for_health: FastAPI) -> None:
    status = await llm_check(google_app_for_health).check()
    assert status.ok and status.detail == MESSAGE == GOOGLE_MODE_DETAIL
    assert "No local user" not in status.detail


async def test_llm_check_in_google_mode_needs_no_user_and_no_database() -> None:
    def broken() -> AsyncSession:
        raise OSError("la base ne doit pas être lue")

    check = LlmKeysCheck(broken, None, {}, {}, lambda: None, google_mode=True)  # type: ignore[arg-type]
    status = await check.check()
    assert status.ok and status.detail == MESSAGE


async def test_llm_check_in_local_mode_is_unchanged() -> None:
    check = LlmKeysCheck(lambda: None, None, {}, {}, lambda: None)  # type: ignore[arg-type]
    status = await check.check()
    assert not status.ok and status.detail == "No local user."


async def test_health_route_is_public_and_not_degraded_by_the_llm_check(
    google_app_for_health: FastAPI,
) -> None:
    # Les sondes réseau des autres services sont remplacées : seul le contrôle `llm` est réel.
    checks = [llm_check(google_app_for_health)]
    google_app_for_health.state.providers.health_checks = checks
    transport = httpx.ASGITransport(app=google_app_for_health)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(HEALTH)  # aucun cookie
    body = response.json()
    assert response.status_code == 200 and body["status"] == "ok"
    assert body["checks"]["llm"] == {"ok": True, "detail": MESSAGE}


async def test_scheduler_and_startup_do_not_depend_on_a_local_user(
    google_settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    app = create_app(
        google_settings.model_copy(update={"scheduler_enabled": True}),
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app):
        assert not hasattr(app.state, "local_user_id")
        await asyncio.sleep(0.5)  # les tâches du démarrage passent
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "Planificateur démarré" in messages and "en échec" not in messages
