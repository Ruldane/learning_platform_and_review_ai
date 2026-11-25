"""GLM (Z.ai) provider: OpenAI-type API, configurable address (`Settings.zai_base_url`).

The key test and the model list go through `GET {base}/models` (inherited), free and independent of
the models' load: 200 with a valid key, 401 otherwise (D39). The models of the presets are added to
the list (D44): `/models` does not return them all.

Reasoning (D44): GLM returns its reasoning in `reasoning_content` and, if the token budget is small,
an empty `content`. GLM-5.3 always reasons (`thinking: disabled` is refused, code 1210, verified),
so
its effort is lowered to `low`. The other models receive `thinking: disabled`.
"""

from collections.abc import Mapping
from typing import Any, ClassVar

from app.providers.llm.errors import PROVIDER_ERROR_CODES
from app.providers.llm.model_defaults import PRESETS
from app.providers.llm.openai import OpenAICompatibleProvider

_ALWAYS_REASONING_PREFIX = "glm-5.3"  # GLM-5.3 et GLM-5.3-FLASH


class GlmProvider(OpenAICompatibleProvider):
    name = "glm"
    label = "GLM (Z.ai)"
    default_base_url: ClassVar[str] = "https://api.z.ai/api/paas/v4/"
    # Z.ai error codes (`{"error": {"code": ...}}`, status 429): shared table (`errors`).
    error_code_messages: ClassVar[Mapping[str, str]] = PROVIDER_ERROR_CODES["glm"]
    # Z.ai returns usage in the stream without it being requested (D44, verified live): no
    # `stream_options`, a parameter its API does not document.
    request_stream_usage: ClassVar[bool] = False

    def __init__(
        self,
        base_url: str | None = None,
        *,
        reasoning_effort: str | None = "low",
        disable_thinking: bool = True,
    ) -> None:
        """`reasoning_effort` (`low`, `high`, `max`) for GLM-5.3, `None` to send nothing;
        `disable_thinking` for the models that accept not reasoning."""
        super().__init__(base_url)
        self._reasoning_effort = reasoning_effort
        self._disable_thinking = disable_thinking

    def extra_body(self, model: str) -> dict[str, Any] | None:
        if model.startswith(_ALWAYS_REASONING_PREFIX):
            return {"reasoning_effort": self._reasoning_effort} if self._reasoning_effort else None
        return {"thinking": {"type": "disabled"}} if self._disable_thinking else None

    async def list_models(self, api_key: str) -> list[str] | None:
        ids = await super().list_models(api_key) or []
        preset_models = [
            c.model for p in PRESETS.values() for c in p.values() if c.provider == "glm"
        ]
        return ids + [m for m in dict.fromkeys(preset_models) if m not in ids]
