"""Services externes tels que les features les reçoivent. Données seulement : la construction
des implémentations concrètes vit dans `app/bootstrap.py`."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from app.core.security import Cipher
from app.providers.embeddings.base import Embedder
from app.providers.health import HealthCheck
from app.providers.keys import KeyProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.pdf.base import PdfTextExtractor
from app.providers.search.base import SearchProvider
from app.providers.storage.base import FileStorage
from app.providers.vector.base import MemoryRepository
from app.providers.web.base import WebReader, YoutubeTranscripts


@dataclass
class Providers:
    """Fournisseurs LLM, fabrique, chiffreur, clés `.env`, fournisseurs de l'écran des clés
    (LLM et Brave) et contrôles de santé."""

    llm: Mapping[str, LlmProvider]
    llm_factory: LlmFactory
    cipher: Cipher
    env_keys: Mapping[str, str | None]
    key_providers: Mapping[str, KeyProvider]
    health_checks: list[HealthCheck] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryProviders:
    """Services de la mémoire : vectorisation, index vectoriel, stockage des fichiers importés,
    extraction PDF, lecture sûre du web et transcriptions YouTube."""

    embedder: Embedder
    index: MemoryRepository
    storage: FileStorage
    pdf: PdfTextExtractor
    web: WebReader
    youtube: YoutubeTranscripts


# Clé Brave de l'utilisateur → client Brave : la clé est lue à chaque recherche (D73).
BraveFactory = Callable[[str], SearchProvider]


@dataclass(frozen=True)
class ResearchProviders:
    """Services de la recherche web : SearXNG (sans clé), fabrique Brave et le lecteur web de la
    mémoire (le même objet que `MemoryProviders.web`)."""

    searxng: SearchProvider
    brave: BraveFactory
    web: WebReader
