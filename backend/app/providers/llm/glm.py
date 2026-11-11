"""Fournisseur GLM (Z.ai) : API de type OpenAI, adresse configurable (`Settings.zai_base_url`).

Le test de clé et la liste des modèles passent par `GET {base}/models` (hérité), gratuit et
indépendant de la charge des modèles : 200 avec une clé valide, 401 sinon (D39).
"""

from typing import ClassVar

from app.providers.llm.openai import OpenAICompatibleProvider


class GlmProvider(OpenAICompatibleProvider):
    name = "glm"
    label = "GLM (Z.ai)"
    default_base_url: ClassVar[str] = "https://api.z.ai/api/paas/v4/"
    # Codes d'erreur Z.ai (`{"error": {"code": ...}}`), renvoyés avec un statut 429.
    error_code_messages: ClassVar[dict[str, str]] = {
        "1113": "Crédit Z.ai insuffisant pour ce modèle.",
        "1305": "Service Z.ai surchargé, réessaie plus tard.",
    }
