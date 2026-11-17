"""Surcharge du modèle par agent (11.2, P17) : validation, lecture d'un réglage stocké qui nomme
un agent disparu, et effet sur les appels journalisés (F6)."""

import logging
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import CostTracker
from app.core.providers import Providers
from app.db.models.agents import LlmCall
from app.features.settings.repository import UserSettingsRepository
from app.features.settings.service import SettingsService
from app.providers.llm.fake import FakeLlmProvider

API = "/api/v1/settings"
GLM = {"provider": "glm", "model": "glm-5.3-flash"}
EXPECTED_422 = {
    "error": {
        "code": "validation_error",
        "message": "Requête invalide : vérifie les champs signalés.",
        "details": {"fields": ["agent_overrides"]},
    }
}


class GlmFake(FakeLlmProvider):
    name = "glm"
    label = "GLM (faux)"


class AnthropicFake(FakeLlmProvider):
    name = "anthropic"
    label = "Anthropic (faux)"


async def put(client: httpx.AsyncClient, **over: Any) -> httpx.Response:
    return await client.put(API, json=(await client.get(API)).json() | over)


async def test_unknown_agent_override_is_422(client: httpx.AsyncClient) -> None:
    r = await put(client, agent_overrides={"inconnu": GLM})
    assert r.status_code == 422 and "inconnu" not in r.text
    assert r.json() == EXPECTED_422


async def test_unknown_agent_with_a_bad_choice_never_echoes_the_name(
    client: httpx.AsyncClient,
) -> None:
    bad = {"provider": "", "model": "MODELE-ECHO-XYZ"}
    r = await put(client, agent_overrides={"agent-fantome-ECHO": bad, "strategist": GLM})
    assert r.status_code == 422 and r.json() == EXPECTED_422
    assert "ECHO" not in r.text


async def test_known_agent_with_a_bad_choice_names_the_field(client: httpx.AsyncClient) -> None:
    r = await put(client, agent_overrides={"strategist": {"provider": "", "model": "ECHO-XYZ"}})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["agent_overrides.strategist.provider"]}
    assert "ECHO-XYZ" not in r.text


async def test_known_agent_override_is_saved_and_listed(client: httpx.AsyncClient) -> None:
    r = await put(client, agent_overrides={"strategist": GLM, "writer": GLM})
    assert r.status_code == 200 and set(r.json()["agent_overrides"]) == {"strategist", "writer"}
    assert (await client.get(API)).json()["agent_overrides"]["strategist"] == GLM
    cleared = await put(client, agent_overrides={})
    assert cleared.json()["agent_overrides"] == {}


async def test_overrides_not_a_mapping_is_422(client: httpx.AsyncClient) -> None:
    r = await put(client, agent_overrides=["strategist"])
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["agent_overrides"]}


async def test_stored_override_of_removed_agent_dropped(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await UserSettingsRepository(db_session, "u1").save_data(
        {
            "debate_rounds": 5,
            "agent_overrides": {"strategist": GLM, "agent-disparu-secret": GLM},
        }
    )
    settings = await SettingsService(db_session, "u1").get()
    assert list(settings.agent_overrides) == ["strategist"]
    assert settings.agent_overrides["strategist"].provider == "glm"
    assert settings.debate_rounds == 5  # le reste des réglages n'est pas perdu
    # Une lecture n'écrit rien dans le journal (le moteur en lit une par appel de modèle).
    assert "agent_overrides" not in "\n".join(record.getMessage() for record in caplog.records)


async def test_removed_agent_is_logged_once_at_save_never_at_read(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await UserSettingsRepository(db_session, "u1").save_data(
        {"agent_overrides": {"strategist": GLM, "agent-disparu-secret": GLM}}
    )
    service = SettingsService(db_session, "u1")
    for _ in range(3):
        await service.get()
    assert not [r for r in caplog.records if "agent_overrides" in r.getMessage()]
    await service.replace(await service.get())
    logged = [r.getMessage() for r in caplog.records if "agent_overrides" in r.getMessage()]
    assert len(logged) == 1 and "agent-disparu-secret" not in logged[0]
    await service.replace(await service.get())  # plus rien à retirer : plus rien à dire
    assert len([r for r in caplog.records if "agent_overrides" in r.getMessage()]) == 1


async def test_stored_overrides_all_removed_gives_empty(db_session: AsyncSession) -> None:
    await UserSettingsRepository(db_session, "u1").save_data({"agent_overrides": {"vieux": GLM}})
    assert (await SettingsService(db_session, "u1").get()).agent_overrides == {}


async def test_stored_overrides_of_known_agents_are_not_logged_as_dropped(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await UserSettingsRepository(db_session, "u1").save_data({"agent_overrides": {"writer": GLM}})
    await SettingsService(db_session, "u1").get()
    assert "agent_overrides" not in "\n".join(r.getMessage() for r in caplog.records)


async def test_get_settings_survives_a_removed_agent(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await UserSettingsRepository(db_session, app.state.local_user_id).save_data(
        {"agent_overrides": {"disparu": GLM, "tutor": GLM}}
    )
    await db_session.commit()
    r = await client.get(API)
    assert r.status_code == 200 and list(r.json()["agent_overrides"]) == ["tutor"]
    # Le réglage ainsi lu se renvoie tel quel, sans 422.
    assert (await client.put(API, json=r.json())).status_code == 200


@pytest.mark.parametrize("agent", ["demo_proponent", "demo_critic"])
async def test_demo_agent_override_is_422_without_echo(
    client: httpx.AsyncClient, agent: str
) -> None:
    """Le catalogue cache les agents de démonstration : le `PUT` ne les accepte pas non plus."""
    r = await put(client, agent_overrides={agent: GLM})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["agent_overrides"]}
    assert agent not in r.text


async def test_stored_override_of_a_demo_agent_is_dropped(db_session: AsyncSession) -> None:
    await UserSettingsRepository(db_session, "u1").save_data(
        {"agent_overrides": {"demo_critic": GLM, "tutor": GLM}}
    )
    settings = await SettingsService(db_session, "u1").get()
    assert list(settings.agent_overrides) == ["tutor"]


async def test_unknown_tier_is_422_without_echoing_the_key(client: httpx.AsyncClient) -> None:
    r = await put(client, tiers={"NOM-DE-NIVEAU-SECRET": GLM})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["tiers"]}
    assert "NOM-DE-NIVEAU-SECRET" not in r.text


async def test_known_tier_with_a_bad_value_still_names_its_path(
    client: httpx.AsyncClient,
) -> None:
    r = await put(client, tiers={"rapide": {"provider": "", "model": "m"}})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["tiers.rapide.provider"]}


async def test_override_never_logged(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await put(client, agent_overrides={"agent-secret-xyz": GLM})
    bad = {"provider": "", "model": "modele-secret-xyz"}
    await put(client, agent_overrides={"strategist": bad})
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "agent-secret-xyz" not in logged and "modele-secret-xyz" not in logged


# --- F6 : l'effet des réglages sur les appels journalisés -------------------------------------


async def journaled_call(
    providers: Providers,
    factory: async_sessionmaker[AsyncSession],
    user_id: str,
    tier: Any,
    agent: str | None,
) -> None:
    """Un appel comme en fait un agent : modèle de la fabrique (réglages lus à cet instant), suivi
    des coûts qui l'écrit dans `llm_calls`."""
    model = await providers.llm_factory.get_chat_model(user_id, tier, agent)
    tracker = CostTracker(
        user_id=user_id,
        session_id="session-1",
        graph="demo",
        bus=EventBus(factory),
        session_factory=factory,
        prices={},
        cap_tokens=300_000,
    )
    chat = model.with_config(metadata={"agent": agent})
    await chat.ainvoke([HumanMessage("un deux trois")], config={"callbacks": [tracker]})


async def logged_models(client: httpx.AsyncClient) -> list[tuple[str, str]]:
    """Les appels du journal (`GET /costs/calls`), du plus ancien au plus récent."""
    items = (await client.get("/api/v1/costs/calls")).json()["items"]
    return [(item["provider"], item["model"]) for item in reversed(items)]


async def test_agent_override_used_by_next_session(
    client: httpx.AsyncClient,
    app: FastAPI,
    providers: Providers,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = app.state.local_user_id
    providers.llm["anthropic"] = AnthropicFake(["réponse un", "réponse deux", "réponse trois"])
    providers.llm["glm"] = GlmFake(["réponse glm"])
    providers.env_keys.update({"anthropic": "cle-a", "glm": "cle-g"})
    await journaled_call(providers, db_session_factory, user, "fort", "strategist")
    assert await logged_models(client) == [("anthropic", "claude-haiku-5-5")]
    r = await put(client, agent_overrides={"strategist": GLM})
    assert r.status_code == 200
    # La session suivante : l'agent surchargé suit son modèle, quel que soit le niveau demandé.
    await journaled_call(providers, db_session_factory, user, "fort", "strategist")
    await journaled_call(providers, db_session_factory, user, "fort", "writer")
    assert await logged_models(client) == [
        ("anthropic", "claude-haiku-5-5"),
        ("glm", "glm-5.3-flash"),
        ("anthropic", "claude-haiku-5-5"),
    ]


async def test_tier_switch_visible_in_llm_calls(
    client: httpx.AsyncClient,
    app: FastAPI,
    providers: Providers,
    db_session: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = app.state.local_user_id
    providers.llm["anthropic"] = AnthropicFake(["réponse un"])
    providers.llm["glm"] = GlmFake(["réponse deux"])
    providers.env_keys.update({"anthropic": "cle-a", "glm": "cle-g"})
    await journaled_call(providers, db_session_factory, user, "fort", None)
    current = (await client.get(API)).json()
    tiers = current["tiers"] | {"fort": {"provider": "glm", "model": "glm-5.3-pro"}}
    assert (await put(client, tiers=tiers)).status_code == 200
    await journaled_call(providers, db_session_factory, user, "fort", None)
    stmt = select(LlmCall.provider, LlmCall.model).order_by(LlmCall.created_at)
    rows = [tuple(row) for row in (await db_session.execute(stmt)).all()]
    assert rows == [("anthropic", "claude-haiku-5-5"), ("glm", "glm-5.3-pro")]
    assert await logged_models(client) == rows
