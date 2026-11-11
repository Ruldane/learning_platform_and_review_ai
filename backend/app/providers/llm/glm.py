"""Fournisseur GLM (Z.ai) : API de type OpenAI, adresse configurable (`Settings.zai_base_url`)."""

from typing import ClassVar

from app.providers.llm import _http
from app.providers.llm.base import KeyTestResult
from app.providers.llm.model_defaults import GLM_FAST
from app.providers.llm.openai import OpenAICompatibleProvider


class GlmProvider(OpenAICompatibleProvider):
    name = "glm"
    label = "GLM (Z.ai)"
    default_base_url: ClassVar[str] = "https://api.z.ai/api/paas/v4/"

    async def list_models(self, api_key: str) -> list[str] | None:
        # La documentation Z.ai ne décrit pas de liste de modèles : saisie libre (D26).
        return None

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Pas de liste : un appel d'un seul token sur le modèle gratuit (aucun coût réel)."""
        body = {
            "model": GLM_FAST,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
        return await _http.check_key(
            self.label, "POST", self._url("chat/completions"), self._headers(api_key), body
        )
