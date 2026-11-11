import json
from collections.abc import Callable

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from app.core.errors import AppError
from app.core.security import SecretUnreadable
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider
from app.providers.llm.glm import GlmProvider
from app.providers.llm.model_defaults import DEFAULT_TIERS, PRESETS
from app.providers.llm.registry import LLM_PROVIDERS, PRICES_PATH

FactoryWith = Callable[..., LlmFactory]


async def test_resolve_uses_tier_then_agent_override(factory_with: FactoryWith) -> None:
    f = factory_with(
        tiers={"fort": ("fake", "m-fort")},
        overrides={"writer": ("fake", "m-writer")},
        keys={"fake": "k"},
    )
    assert (await f.resolve("u1", "fort")).model == "m-fort"
    assert (await f.resolve("u1", "fort", agent="writer")).model == "m-writer"


async def test_get_chat_model_builds_with_resolved_key(
    factory_with: FactoryWith, fake_provider: FakeLlmProvider
) -> None:
    f = factory_with(tiers={"rapide": ("fake", "m1")}, keys={"fake": "k-123"})
    await f.get_chat_model("u1", "rapide")
    assert fake_provider.built == [("m1", "k-123")]


async def test_missing_key_is_readable_error(factory_with: FactoryWith) -> None:
    f = factory_with(tiers={"fort": ("fake", "m")}, keys={})
    with pytest.raises(AppError) as e:
        await f.get_chat_model("u1", "fort")
    assert e.value.code == "llm_key_missing" and "« fort »" in e.value.message
    assert e.value.details == {"provider": "fake", "tier": "fort"}


async def test_unreadable_key_is_readable_error(factory_with: FactoryWith) -> None:
    f = factory_with(tiers={"fort": ("fake", "m")}, keys=SecretUnreadable)
    with pytest.raises(AppError) as e:
        await f.get_chat_model("u1", "fort")
    assert e.value.code == "llm_key_unreadable"
    assert e.value.status_code == 400


async def test_unknown_provider_is_readable_error(factory_with: FactoryWith) -> None:
    f = factory_with(tiers={"fort": ("inconnu", "m")}, keys={"inconnu": "secret-value-123"})
    with pytest.raises(AppError) as e:
        await f.get_chat_model("u1", "fort")
    assert e.value.code == "llm_provider_unknown" and e.value.status_code == 400
    assert "secret-value-123" not in e.value.message


async def test_base_url_is_passed_to_the_provider(
    factory_with: FactoryWith, fake_provider: FakeLlmProvider
) -> None:
    f = factory_with(
        tiers={"rapide": ("fake", "m")}, keys={"fake": "k"}, base_urls={"fake": "https://x.test/"}
    )
    await f.get_chat_model("u1", "rapide")
    assert fake_provider.base_urls == ["https://x.test/"]


async def test_fake_model_streams_and_reports_usage(fake_provider: FakeLlmProvider) -> None:
    model = fake_provider.build("m", "fake-key")
    chunks = [c async for c in model.astream("bonjour")]
    assert "".join(str(c.content) for c in chunks).strip() == fake_provider.responses[0]
    assert len(chunks) > 1
    last = chunks[-1]
    assert isinstance(last, AIMessageChunk)
    assert last.usage_metadata == {"input_tokens": 1, "output_tokens": 4, "total_tokens": 5}


async def test_fake_model_returns_responses_in_order_and_records_messages(
    fake_provider: FakeLlmProvider,
) -> None:
    model = fake_provider.build("m", "fake-key")
    first = await model.ainvoke([HumanMessage("un deux trois")])
    second = await model.ainvoke("encore")
    assert (first.content, second.content) == tuple(fake_provider.responses)
    assert first.usage_metadata == {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7}
    assert [[m.content for m in call] for call in fake_provider.received] == [
        ["un deux trois"],
        ["encore"],
    ]


async def test_fake_test_key_accepts_only_the_valid_key(fake_provider: FakeLlmProvider) -> None:
    assert (await fake_provider.test_key("fake-key")).ok
    refused = await fake_provider.test_key("nope")
    assert not refused.ok and "nope" not in refused.message


def test_glm_uses_configurable_base_url() -> None:
    model = GlmProvider().build("glm-x", "k", base_url="https://exemple.test/v4/")
    assert str(model.openai_api_base).startswith("https://exemple.test/v4")  # type: ignore[attr-defined]


def test_real_providers_build_with_retries_and_streaming() -> None:
    for name in ("anthropic", "openai", "glm"):
        model = LLM_PROVIDERS[name].build("un-modele", "k")
        assert model.streaming is True  # type: ignore[attr-defined]
        assert model.max_retries == 2  # type: ignore[attr-defined]


def test_registry_exposes_the_three_providers() -> None:
    assert set(LLM_PROVIDERS) == {"anthropic", "openai", "glm"}
    assert [p.label for p in LLM_PROVIDERS.values()] == ["Anthropic", "OpenAI", "GLM (Z.ai)"]


def test_every_default_model_has_a_price() -> None:
    prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    models = {c.model for preset in PRESETS.values() for c in preset.values()}
    models |= {c.model for c in DEFAULT_TIERS.values()}
    assert models <= set(prices)
    for entry in prices.values():
        assert set(entry) == {"input_per_mtok", "output_per_mtok"}
        assert all(isinstance(v, int | float) and v >= 0 for v in entry.values())
