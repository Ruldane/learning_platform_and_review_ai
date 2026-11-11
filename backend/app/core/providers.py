"""Services externes tels que les features les reçoivent. Données seulement : la construction
des implémentations concrètes vit dans `app/bootstrap.py`."""

from collections.abc import Mapping
from dataclasses import dataclass

from app.core.security import Cipher
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory


@dataclass
class Providers:
    """Fournisseurs LLM, fabrique, chiffreur et clés `.env`. Le champ `health_checks` s'ajoute
    avec les contrôles de santé (tâche 0.9)."""

    llm: Mapping[str, LlmProvider]
    llm_factory: LlmFactory
    cipher: Cipher
    env_keys: Mapping[str, str | None]
