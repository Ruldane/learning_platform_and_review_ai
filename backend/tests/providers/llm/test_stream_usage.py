"""Les appels en flux des fournisseurs de type OpenAI rapportent l'usage (tokens, coût, plafond).

Aucun réseau : le client HTTP du SDK (httpx2) reçoit un transport simulé qui enregistre le corps de
la requête et répond un flux SSE.
"""

import json
from collections.abc import Callable
from functools import partial
from typing import Any

import httpx2
import pytest
from langchain_openai import ChatOpenAI

from app.providers.llm import openai as openai_module
from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.base import LLM_CALL_TIMEOUT_S
from app.providers.llm.glm import GlmProvider
from app.providers.llm.openai import OpenAIProvider

_CHUNK = {"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "m"}


def _sse(include_usage: bool) -> bytes:
    """Flux d'une réponse « Bonjour » ; l'usage arrive dans un dernier morceau sans choix."""
    delta = {"role": "assistant", "content": "Bonjour"}
    chunks: list[dict[str, Any]] = [
        {**_CHUNK, "choices": [{"index": 0, "delta": delta}]},
        {**_CHUNK, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
    ]
    if include_usage:
        usage = {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9}
        chunks.append({**_CHUNK, "choices": [], "usage": usage})
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks] + ["data: [DONE]\n\n"]
    return "".join(lines).encode()


def _recording_client(bodies: list[dict[str, Any]], usage_unasked: bool) -> httpx2.AsyncClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        bodies.append(body)
        asked = body.get("stream_options", {}).get("include_usage", False)
        return httpx2.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(asked or usage_unasked),
        )

    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: httpx2.AsyncClient) -> None:
    factory: Callable[..., ChatOpenAI] = partial(ChatOpenAI, http_async_client=client)
    monkeypatch.setattr(openai_module, "ChatOpenAI", factory)


async def test_openai_requests_usage_while_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    bodies: list[dict[str, Any]] = []
    _patch_client(monkeypatch, _recording_client(bodies, usage_unasked=False))
    reply = await OpenAIProvider().build("gpt-test", "sk-test").ainvoke("Salut")
    assert bodies[0]["stream"] is True
    assert bodies[0]["stream_options"] == {"include_usage": True}
    usage = getattr(reply, "usage_metadata", None)
    assert usage is not None and usage["input_tokens"] == 7 and usage["output_tokens"] == 2


async def test_glm_keeps_its_unasked_usage_and_sends_no_stream_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Z.ai renvoie l'usage sans qu'on le demande (D44, vérifié en réel) : rien n'est ajouté à sa
    # requête, pour ne pas risquer un paramètre qu'il refuserait.
    bodies: list[dict[str, Any]] = []
    _patch_client(monkeypatch, _recording_client(bodies, usage_unasked=True))
    reply = await GlmProvider().build("glm-5.3-flash", "k").ainvoke("Salut")
    assert "stream_options" not in bodies[0]
    usage = getattr(reply, "usage_metadata", None)
    assert usage is not None and usage["output_tokens"] == 2


def test_every_provider_build_sets_the_per_call_timeout() -> None:
    openai_model = OpenAIProvider().build("gpt-test", "sk-test")
    glm_model = GlmProvider().build("glm-5.3-flash", "k")
    anthropic_model = AnthropicProvider().build("claude-test", "k")
    assert getattr(openai_model, "request_timeout", None) == LLM_CALL_TIMEOUT_S
    assert getattr(glm_model, "request_timeout", None) == LLM_CALL_TIMEOUT_S
    assert getattr(anthropic_model, "default_request_timeout", None) == LLM_CALL_TIMEOUT_S


@pytest.mark.parametrize(
    ("build", "label"),
    [
        (OpenAIProvider().build, "OpenAI"),
        (GlmProvider().build, "GLM (Z.ai)"),
        (AnthropicProvider().build, "Anthropic"),
    ],
)
def test_build_names_the_provider_for_readable_errors(
    build: Callable[[str, str], Any], label: str
) -> None:
    assert (build("m", "k").metadata or {})["tremplin_provider_label"] == label
