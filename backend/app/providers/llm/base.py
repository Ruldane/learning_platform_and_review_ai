"""LLM interface: shared types, and the protocols of the providers and of the injected readers.

No import from `app/features/`: the factory depends only on the protocols below; the composition
with the settings feature happens in `app/bootstrap.py`.
"""

from typing import Literal, Protocol

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

# SDK (httpx) timeout: connection, and waiting for EACH chunk of the response, not for the whole
# call. A streamed response that keeps arriving (GLM-5.3 reasoning, chunk after
# chunk) never triggers it (check 5.18): hence the total deadline below.
LLM_CALL_TIMEOUT_S = 45
# Total deadline of a call (adjustable: `LLM_CALL_DEADLINE_S`), set by the factory in the
# model's metadata under `CALL_DEADLINE_KEY` and applied by `call_with_retries`; beyond it,
# the call is a timeout and is retried. Equal to the longest node cap (600 s: Writer,
# Strategist, Examiner): it never cuts a call before its node (the node's timer starts
# first); it only bounds a call outside any shorter cap. The Tutor has its own deadline,
# shorter (`TUTOR_CALL_TIMEOUT_S`, D115 no. 17).
LLM_CALL_DEADLINE_S = 600.0
CALL_DEADLINE_KEY = "tremplin_call_deadline_s"
# Mark (`additional_kwargs` of a `SystemMessage`) of the fixed start of a session's prompt: the
# providers that can cache it do so (Anthropic, `cache_control`), the others
# ignore it. The marked text must stay identical from one call to the next (byte for byte).
CACHE_PREFIX_KEY = "tremplin_cache_prefix"

Tier = Literal["fast", "standard", "strong", "vision"]
TIERS: tuple[Tier, ...] = ("fast", "standard", "strong", "vision")


class ModelChoice(BaseModel):
    """Provider and model identifier chosen for a tier or an agent."""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)


class KeyTestResult(BaseModel):
    """Result of a key test: `message` is in English and never contains the key."""

    ok: bool
    message: str


class LlmProvider(Protocol):
    """A chat model provider (Anthropic, OpenAI, GLM, or a fake one for the tests)."""

    name: str
    label: str

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel: ...

    async def list_models(self, api_key: str) -> list[str] | None:
        """Available identifiers, or `None` if the provider has no list API."""
        ...

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Checks the key without ever raising (network and authentication errors included)."""
        ...


class ModelChoiceReader(Protocol):
    async def get_model_choice(
        self, user_id: str, tier: Tier, agent: str | None
    ) -> ModelChoice: ...


class KeyReader(Protocol):
    async def get_key(self, user_id: str, provider: str) -> str | None:
        """Plain key, or `None` if absent. Raises `SecretUnreadable` if it is unreadable."""
        ...
