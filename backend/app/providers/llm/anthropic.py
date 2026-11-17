"""Fournisseur Anthropic (Claude) : `langchain-anthropic` pour le chat, `httpx` pour la clé."""

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import SecretStr

from app.providers.llm import _http
from app.providers.llm.base import CACHE_PREFIX_KEY, LLM_CALL_TIMEOUT_S, KeyTestResult

_API_URL = "https://api.anthropic.com"
_API_VERSION = "2023-06-01"
_MAX_PAGES = 50  # garde-fou contre un curseur qui ne finit jamais


def _cached(message: BaseMessage) -> BaseMessage:
    """Un `SystemMessage` marqué (`CACHE_PREFIX_KEY`) devient un bloc texte portant
    `cache_control` : Anthropic met en cache tout le début du prompt jusqu'à ce bloc."""
    if (
        isinstance(message, SystemMessage)
        and message.additional_kwargs.get(CACHE_PREFIX_KEY)
        and isinstance(message.content, str)
    ):
        block = {"type": "text", "text": message.content, "cache_control": {"type": "ephemeral"}}
        return SystemMessage(content=[block], additional_kwargs=message.additional_kwargs)
    return message


class _CachingChatAnthropic(ChatAnthropic):
    """`ChatAnthropic` qui pose `cache_control` sur le début fixe marqué par l'appelant."""

    def _get_request_payload(
        self, input_: Any, *, stop: list[str] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        messages = [_cached(message) for message in self._convert_input(input_).to_messages()]
        return super()._get_request_payload(messages, stop=stop, **kwargs)


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key, "anthropic-version": _API_VERSION}


class AnthropicProvider:
    name = "anthropic"
    label = "Anthropic"

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel:
        return _CachingChatAnthropic(
            model=model,  # type: ignore[call-arg]
            api_key=SecretStr(api_key),
            base_url=base_url,
            timeout=LLM_CALL_TIMEOUT_S,
            max_retries=0,  # les nouveaux essais appartiennent à `invoke_agent` (D44)
            streaming=True,
            metadata={
                "tremplin_provider": self.name,
                "tremplin_provider_label": self.label,
                "tremplin_model": model,
            },
        )

    async def list_models(self, api_key: str) -> list[str] | None:
        ids: list[str] = []
        params: dict[str, str | int] = {"limit": 1000}
        for _ in range(_MAX_PAGES):
            page, cursor = await _http.get_model_page(
                self.label, f"{_API_URL}/v1/models", _headers(api_key), params
            )
            ids += page
            if cursor is None:
                return ids
            params["after_id"] = cursor
        return ids

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Liste les modèles : aucun token dépensé."""
        return await _http.check_key(
            self.label, "GET", f"{_API_URL}/v1/models?limit=1", _headers(api_key)
        )
