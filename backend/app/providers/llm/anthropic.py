"""Fournisseur Anthropic (Claude) : `langchain-anthropic` pour le chat, `httpx` pour la clé."""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from app.providers.llm import _http
from app.providers.llm.base import KeyTestResult

_TIMEOUT_S = 120
_API_URL = "https://api.anthropic.com"
_API_VERSION = "2023-06-01"


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key, "anthropic-version": _API_VERSION}


class AnthropicProvider:
    name = "anthropic"
    label = "Anthropic"

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel:
        return ChatAnthropic(
            model=model,  # type: ignore[call-arg]
            api_key=SecretStr(api_key),
            base_url=base_url,
            timeout=_TIMEOUT_S,
            max_retries=2,
            streaming=True,
        )

    async def list_models(self, api_key: str) -> list[str] | None:
        ids: list[str] = []
        params: dict[str, str | int] = {"limit": 1000}
        while True:
            page = await _http.get_json(
                self.label, f"{_API_URL}/v1/models", _headers(api_key), params
            )
            ids += [m["id"] for m in page["data"]]
            if not page.get("has_more") or not page.get("last_id"):
                return ids
            params["after_id"] = page["last_id"]

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Liste les modèles : aucun token dépensé."""
        return await _http.check_key(
            self.label, "GET", f"{_API_URL}/v1/models?limit=1", _headers(api_key)
        )
