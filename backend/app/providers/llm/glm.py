"""Fournisseur GLM (Z.ai) : API de type OpenAI, adresse configurable (`Settings.zai_base_url`).

Le test de clé et la liste des modèles passent par `GET {base}/models` (hérité), gratuit et
indépendant de la charge des modèles : 200 avec une clé valide, 401 sinon (D39). Les modèles des
préréglages sont ajoutés à la liste (D44) : `/models` ne les renvoie pas tous.

Raisonnement (D44) : GLM renvoie sa réflexion dans `reasoning_content` et, si le budget de tokens
est petit, un `content` vide. GLM-5.3 raisonne toujours (`thinking: disabled` est refusé, code
1210, vérifié) : on abaisse son effort à `low`. Les autres modèles reçoivent `thinking: disabled`.
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
    # Codes d'erreur Z.ai (`{"error": {"code": ...}}`, statut 429) : table commune (`errors`).
    error_code_messages: ClassVar[Mapping[str, str]] = PROVIDER_ERROR_CODES["glm"]
    # Z.ai renvoie l'usage en flux sans qu'on le demande (D44, vérifié en réel) : pas de
    # `stream_options`, paramètre que son API ne documente pas.
    request_stream_usage: ClassVar[bool] = False

    def __init__(
        self,
        base_url: str | None = None,
        *,
        reasoning_effort: str | None = "low",
        disable_thinking: bool = True,
    ) -> None:
        """`reasoning_effort` (`low`, `high`, `max`) pour GLM-5.3, `None` pour ne rien envoyer ;
        `disable_thinking` pour les modèles qui acceptent de ne pas raisonner."""
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
