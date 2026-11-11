from collections.abc import Iterator

import httpx
import pytest
import respx

from app.core.errors import AppError
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


GLM_MODELS = "https://exemple.test/v4/models"
GLM_LIST = {"object": "list", "data": [{"id": "glm-4.5", "object": "model", "owned_by": "z-ai"}]}


async def test_glm_test_key_and_list_models_use_free_models_endpoint(
    mock: respx.MockRouter,
) -> None:
    # `GET /models` ne coûte rien et ne dépend pas de la charge d'un modèle gratuit.
    route = mock.get(GLM_MODELS).respond(200, json=GLM_LIST)
    chat = mock.post("https://exemple.test/v4/chat/completions")
    provider = GlmProvider(base_url="https://exemple.test/v4/")
    result = await provider.test_key(KEY)
    assert result.ok and result.message == "Clé valide."
    assert await provider.list_models(KEY) == ["glm-4.5"]
    assert route.calls.last.request.headers["authorization"] == f"Bearer {KEY}"
    assert not chat.called


async def test_glm_test_key_refused_on_401(mock: respx.MockRouter) -> None:
    mock.get("https://api.z.ai/api/paas/v4/models").respond(
        401, json={"error": {"code": "401", "message": "token expired or incorrect"}}
    )
    result = await GlmProvider().test_key(KEY)
    assert not result.ok
    assert result.message == "Clé refusée par GLM (Z.ai)."
    assert KEY not in result.message


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("1113", "Crédit Z.ai insuffisant pour ce modèle."),
        ("1305", "Service Z.ai surchargé, réessaie plus tard."),
        (
            "9999",
            "Limite de requêtes ou crédit épuisé chez GLM (Z.ai), réessaie plus tard.",
        ),
    ],
)
async def test_glm_429_messages_are_readable(
    mock: respx.MockRouter, code: str, message: str
) -> None:
    body = {"error": {"code": code, "message": f"détail fournisseur {KEY}"}}
    mock.get(GLM_MODELS).respond(429, json=body)
    result = await GlmProvider(base_url="https://exemple.test/v4/").test_key(KEY)
    assert not result.ok
    assert result.message == message
    assert KEY not in result.message


@pytest.mark.parametrize(
    ("provider", "url"),
    [
        (AnthropicProvider(), "https://api.anthropic.com/v1/models"),
        (OpenAIProvider(), "https://api.openai.com/v1/models"),
    ],
)
async def test_429_without_known_code_is_readable(
    mock: respx.MockRouter, provider: AnthropicProvider, url: str
) -> None:
    mock.get(url).respond(429, text="<html>trop</html>")
    result = await provider.test_key(KEY)
    assert not result.ok
    assert result.message == (
        f"Limite de requêtes ou crédit épuisé chez {provider.label}, réessaie plus tard."
    )


async def test_glm_list_models_failure_is_readable_error(mock: respx.MockRouter) -> None:
    mock.get(GLM_MODELS).respond(429, json={"error": {"code": "1305", "message": "x"}})
    with pytest.raises(AppError) as e:
        await GlmProvider(base_url="https://exemple.test/v4/").list_models(KEY)
    assert e.value.code == "llm_models_unavailable" and KEY not in e.value.message


BAD_KEYS = ["sk-clé-é", "sk-“smart”", "sk-ligne\nsuivante"]
PROVIDERS = [AnthropicProvider, OpenAIProvider, GlmProvider]


@pytest.mark.parametrize("bad_key", BAD_KEYS)
@pytest.mark.parametrize("provider_cls", PROVIDERS)
async def test_test_key_with_invalid_characters_does_not_raise(
    mock: respx.MockRouter, provider_cls: type[AnthropicProvider], bad_key: str
) -> None:
    result = await provider_cls().test_key(bad_key)
    assert not result.ok
    assert result.message == "La clé contient des caractères invalides."
    assert bad_key not in result.message
    assert not mock.calls


@pytest.mark.parametrize("bad_key", BAD_KEYS)
@pytest.mark.parametrize("provider_cls", PROVIDERS)
async def test_list_models_with_invalid_characters_is_readable_error(
    mock: respx.MockRouter, provider_cls: type[AnthropicProvider], bad_key: str
) -> None:
    with pytest.raises(AppError) as e:
        await provider_cls().list_models(bad_key)
    assert e.value.code == "llm_models_unavailable"
    assert bad_key not in e.value.message
    assert not mock.calls


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": None},
        {"data": "texte"},
        {"data": [{"name": "x"}]},
        {"data": [None]},
        {"data": [{"id": 3}]},
        [1, 2],
    ],
)
@pytest.mark.parametrize(
    ("provider", "url"),
    [
        (AnthropicProvider(), "https://api.anthropic.com/v1/models"),
        (OpenAIProvider(), "https://api.openai.com/v1/models"),
    ],
)
async def test_list_models_malformed_payload_is_readable_error(
    mock: respx.MockRouter, provider: AnthropicProvider, url: str, payload: object
) -> None:
    mock.get(url).respond(200, json=payload)
    with pytest.raises(AppError) as e:
        await provider.list_models(KEY)
    assert e.value.code == "llm_models_unavailable" and e.value.status_code == 502
    assert KEY not in e.value.message


async def test_list_models_non_json_body_is_readable_error(mock: respx.MockRouter) -> None:
    mock.get("https://api.openai.com/v1/models").respond(200, text="<html>")
    with pytest.raises(AppError) as e:
        await OpenAIProvider().list_models(KEY)
    assert e.value.code == "llm_models_unavailable"


async def test_anthropic_list_models_follows_pagination(mock: respx.MockRouter) -> None:
    route = mock.get("https://api.anthropic.com/v1/models")
    route.side_effect = [
        httpx.Response(200, json={"data": [{"id": "a"}], "has_more": True, "last_id": "a"}),
        httpx.Response(200, json={"data": [{"id": "b"}], "has_more": False, "last_id": "b"}),
    ]
    assert await AnthropicProvider().list_models(KEY) == ["a", "b"]
    assert route.calls.last.request.url.params["after_id"] == "a"
