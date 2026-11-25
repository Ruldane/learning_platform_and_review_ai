"""OpenAI provider, and the common base of OpenAI-type providers (Z.ai's GLM)."""

from collections.abc import Mapping
from typing import Any, ClassVar

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.providers.llm import _http
from app.providers.llm.base import LLM_CALL_TIMEOUT_S, KeyTestResult
from app.providers.llm.errors import PROVIDER_ERROR_CODES


class OpenAICompatibleProvider:
    """OpenAI-type API: configurable `base_url`, model list through `GET /models`."""

    name: str = "openai"
    label: str = "OpenAI"
    default_base_url: ClassVar[str] = "https://api.openai.com/v1/"
    # French messages by error code of the response body (see `_http.check_key`); the table
    # shared is `errors.PROVIDER_ERROR_CODES`, also read for chat calls.
    error_code_messages: ClassVar[Mapping[str, str]] = {}
    # Request the usage in the stream (`stream_options.include_usage`): without it, OpenAI's API
    # returns no token in the stream (cost at 0, cap never reached), and `langchain_openai` only
    # requests it by default without `base_url`, which we always pass.
    request_stream_usage: ClassVar[bool] = True

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.default_base_url

    def extra_body(self, model: str) -> dict[str, Any] | None:
        """Provider-specific parameters added to the body of each request (none here)."""
        return None

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel:
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url or self._base_url,
            timeout=LLM_CALL_TIMEOUT_S,
            max_retries=0,  # new attempts belong to `invoke_agent` (D44)
            streaming=True,
            stream_usage=self.request_stream_usage or None,  # None: the SDK's default setting
            extra_body=self.extra_body(model),
            metadata={
                "tremplin_provider": self.name,
                "tremplin_provider_label": self.label,
                "tremplin_model": model,
            },
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
        """Lists the models: no token spent."""
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
    error_code_messages: ClassVar[Mapping[str, str]] = PROVIDER_ERROR_CODES["openai"]
