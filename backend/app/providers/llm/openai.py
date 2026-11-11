"""Fournisseur OpenAI, et base commune des fournisseurs de type OpenAI (GLM de Z.ai)."""

from typing import ClassVar

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.providers.llm import _http
from app.providers.llm.base import KeyTestResult

_TIMEOUT_S = 120


class OpenAICompatibleProvider:
    """API de type OpenAI : `base_url` configurable, liste des modèles par `GET /models`."""

    name: str = "openai"
    label: str = "OpenAI"
    default_base_url: ClassVar[str] = "https://api.openai.com/v1/"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.default_base_url

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel:
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url or self._base_url,
            timeout=_TIMEOUT_S,
            max_retries=2,
            streaming=True,
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url.rstrip('/')}/{path}"

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    async def list_models(self, api_key: str) -> list[str] | None:
        page = await _http.get_json(self.label, self._url("models"), self._headers(api_key), {})
        return [m["id"] for m in page["data"]]

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Liste les modèles : aucun token dépensé."""
        return await _http.check_key(self.label, "GET", self._url("models"), self._headers(api_key))


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    label = "OpenAI"
