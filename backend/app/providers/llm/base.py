"""Interface LLM : types partagés, protocoles des fournisseurs et des lecteurs injectés.

Aucun import de `app/features/` : la fabrique ne dépend que des protocoles ci-dessous, la
composition avec la feature réglages se fait dans `app/bootstrap.py`.
"""

from typing import Literal, Protocol

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

# Délai du SDK (httpx) : connexion, et attente de CHAQUE morceau de la réponse, pas de l'appel
# entier. Une réponse en flux qui continue d'arriver (réflexion de GLM-5.3, morceau après
# morceau) ne le déclenche jamais (contrôle 5.18) : d'où l'échéance totale ci-dessous.
LLM_CALL_TIMEOUT_S = 45
# Échéance totale d'un appel (réglable : `LLM_CALL_DEADLINE_S`), posée par la fabrique dans les
# métadonnées du modèle sous `CALL_DEADLINE_KEY` et appliquée par `call_with_retries` ; au-delà,
# l'appel est un délai dépassé, retenté. Égale au plus long plafond de nœud (600 s : Rédacteur,
# Stratège, Examinateur) : elle ne coupe jamais un appel avant son nœud (le minuteur du nœud
# part avant), elle borne seulement un appel hors de tout plafond plus court. Le Tuteur a sa
# propre échéance, plus courte (`TUTOR_CALL_TIMEOUT_S`, D115 n° 17).
LLM_CALL_DEADLINE_S = 600.0
CALL_DEADLINE_KEY = "tremplin_call_deadline_s"

Tier = Literal["rapide", "standard", "fort", "vision"]
TIERS: tuple[Tier, ...] = ("rapide", "standard", "fort", "vision")


class ModelChoice(BaseModel):
    """Fournisseur et identifiant de modèle retenus pour un niveau ou un agent."""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)


class KeyTestResult(BaseModel):
    """Résultat d'un test de clé : `message` est en français et ne contient jamais la clé."""

    ok: bool
    message: str


class LlmProvider(Protocol):
    """Un fournisseur de modèles de chat (Anthropic, OpenAI, GLM, faux pour les tests)."""

    name: str
    label: str

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel: ...

    async def list_models(self, api_key: str) -> list[str] | None:
        """Identifiants disponibles, ou `None` si le fournisseur n'a pas d'API de liste."""
        ...

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Vérifie la clé sans jamais lever (erreurs réseau et d'authentification incluses)."""
        ...


class ModelChoiceReader(Protocol):
    async def get_model_choice(
        self, user_id: str, tier: Tier, agent: str | None
    ) -> ModelChoice: ...


class KeyReader(Protocol):
    async def get_key(self, user_id: str, provider: str) -> str | None:
        """Clé en clair, ou `None` si absente. Lève `SecretUnreadable` si elle est illisible."""
        ...
