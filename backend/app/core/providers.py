"""Services externes tels que les features les reçoivent. Données seulement : la construction
des implémentations concrètes vit dans `app/bootstrap.py`."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.security import Cipher
from app.providers.embeddings.base import Embedder
from app.providers.health import HealthCheck
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.vector.base import MemoryRepository


@dataclass
class Providers:
    """Fournisseurs LLM, fabrique, chiffreur, clés `.env` et contrôles de santé."""

    llm: Mapping[str, LlmProvider]
    llm_factory: LlmFactory
    cipher: Cipher
    env_keys: Mapping[str, str | None]
    health_checks: list[HealthCheck] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryProviders:
    """Services de la mémoire : vectorisation et index vectoriel (étendu en 2.4 : stockage de
    fichiers, extraction PDF, lecture web, transcriptions YouTube)."""

    embedder: Embedder
    index: MemoryRepository
