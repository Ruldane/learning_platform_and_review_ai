from collections.abc import Iterator

import httpx
import pytest
import respx

from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.glm import GlmProvider
from app.providers.llm.openai import OpenAIProvider

KEY = "sk-secret-key-abcdef123456"


@pytest.fixture
def mock() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        yield router


async def test_anthropic_test_key_refused_on_401(mock: respx.MockRouter) -> None:
    mock.get("https://api.anthropic.com/v1/models").respond(
        401, json={"type": "error", "error": {"type": "authentication_error", "message": "bad"}}
    )
    result = await AnthropicProvider().test_key(KEY)
    assert not result.ok
    assert result.message == "Clé refusée par Anthropic."
    assert KEY not in result.message


async def test_anthropic_test_key_ok_and_lists_models(mock: respx.MockRouter) -> None:
    payload = {
        "data": [
            {
                "type": "model",
                "id": "claude-haiku-5-5",
                "display_name": "Haiku",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
        "has_more": False,
        "first_id": "claude-haiku-5-5",
        "last_id": "claude-haiku-5-5",
    }
    mock.get("https://api.anthropic.com/v1/models").respond(200, json=payload)
    provider = AnthropicProvider()
    assert (await provider.test_key(KEY)).ok
    assert await provider.list_models(KEY) == ["claude-haiku-5-5"]


async def test_anthropic_test_key_network_error_does_not_raise(mock: respx.MockRouter) -> None:
    mock.get("https://api.anthropic.com/v1/models").mock(side_effect=httpx.ConnectError("boom"))
    result = await AnthropicProvider().test_key(KEY)
    assert not result.ok and KEY not in result.message


async def test_openai_test_key_refused_on_401(mock: respx.MockRouter) -> None:
    mock.get("https://api.openai.com/v1/models").respond(
        401, json={"error": {"message": f"Incorrect API key provided: {KEY}", "type": "x"}}
    )
    result = await OpenAIProvider().test_key(KEY)
    assert not result.ok
    assert result.message == "Clé refusée par OpenAI."
    assert KEY not in result.message


async def test_openai_test_key_ok_and_lists_models(mock: respx.MockRouter) -> None:
    mock.get("https://api.openai.com/v1/models").respond(
        200, json={"object": "list", "data": [{"id": "gpt-6-luna", "object": "model"}]}
    )
    provider = OpenAIProvider()
    assert (await provider.test_key(KEY)).ok
    assert await provider.list_models(KEY) == ["gpt-6-luna"]


async def test_openai_test_key_timeout_does_not_raise(mock: respx.MockRouter) -> None:
    mock.get("https://api.openai.com/v1/models").mock(side_effect=httpx.ReadTimeout("slow"))
    result = await OpenAIProvider().test_key(KEY)
    assert not result.ok and KEY not in result.message


async def test_glm_has_no_model_list() -> None:
    assert await GlmProvider().list_models(KEY) is None


async def test_glm_test_key_uses_one_token_call(mock: respx.MockRouter) -> None:
    message = {"role": "assistant", "content": "a"}
    route = mock.post("https://exemple.test/v4/chat/completions").respond(
        200,
        json={
            "id": "x",
            "object": "chat.completion",
            "created": 1,
            "model": "glm-4.7-flash",
            "choices": [{"index": 0, "finish_reason": "length", "message": message}],
        },
    )
    result = await GlmProvider(base_url="https://exemple.test/v4/").test_key(KEY)
    assert result.ok
    assert b'"max_tokens":1' in route.calls.last.request.content.replace(b" ", b"")


async def test_glm_test_key_refused_on_401(mock: respx.MockRouter) -> None:
    mock.post("https://api.z.ai/api/paas/v4/chat/completions").respond(
        401, json={"error": {"code": "1000", "message": "bad"}}
    )
    result = await GlmProvider().test_key(KEY)
    assert not result.ok
    assert result.message == "Clé refusée par GLM (Z.ai)."
    assert KEY not in result.message
