"""Fournisseur OpenAI, et base commune des fournisseurs de type OpenAI (GLM de Z.ai)."""

from typing import Any, ClassVar

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
    # Messages français par code d'erreur du corps de réponse (voir `_http.check_key`).
    error_code_messages: ClassVar[dict[str, str]] = {}

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.default_base_url

    def extra_body(self, model: str) -> dict[str, Any] | None:
        """Paramètres propres au fournisseur ajoutés au corps de chaque requête (aucun ici)."""
        return None

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel:
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url or self._base_url,
            timeout=_TIMEOUT_S,
            max_retries=0,  # les nouveaux essais appartiennent à `invoke_agent` (D44)
            streaming=True,
            extra_body=self.extra_body(model),
            metadata={"tremplin_provider": self.name, "tremplin_model": model},
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url.rstrip('/')}/{path}"

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    async def list_models(self, api_key: str) -> list[str] | None:
        ids, _ = await _http.get_model_page(
            self.label, self._url("models"), self._headers(api_key), {}
        )
        return ids

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Liste les modèles : aucun token dépensé."""
        return await _http.check_key(
            self.label,
            "GET",
            self._url("models"),
            self._headers(api_key),
            code_messages=self.error_code_messages,
        )


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    label = "OpenAI"
