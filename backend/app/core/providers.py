"""Services externes tels que les features les reçoivent. Données seulement : la construction
des implémentations concrètes vit dans `app/bootstrap.py`."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from app.core.security import Cipher
from app.providers.auth.base import OidcProvider
from app.providers.embeddings.base import Embedder, EmbeddingProgressSource
from app.providers.fonts.base import FontSource
from app.providers.health import HealthCheck
from app.providers.keys import KeyProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.pdf.base import HtmlPdfRenderer, PdfLayoutExtractor, PdfTextExtractor
from app.providers.search.base import SearchProvider
from app.providers.storage.base import FileStorage
from app.providers.vector.base import MemoryRepository
from app.providers.web.base import WebFetcher, WebReader, YoutubeTranscripts


@dataclass
class Providers:
    """Fournisseurs LLM, fabrique, chiffreur, clés `.env`, fournisseurs de l'écran des clés
    (LLM et Brave), contrôles de santé, connexion OpenID Connect (`None` en mode local) et
    progression du modèle d'embeddings (`GET /health/embedding`, P13)."""

    llm: Mapping[str, LlmProvider]
    llm_factory: LlmFactory
    cipher: Cipher
    env_keys: Mapping[str, str | None]
    key_providers: Mapping[str, KeyProvider]
    health_checks: list[HealthCheck] = field(default_factory=list)
    oidc: OidcProvider | None = None
    embedding: EmbeddingProgressSource | None = None


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
    """Services de la recherche web : SearXNG (sans clé), fabrique Brave, le lecteur web de la
    mémoire (le même objet que `MemoryProviders.web`) et un fetcher sûr (garde SSRF) pour les
    copies locales des PDF libres des ressources (D91)."""

    searxng: SearchProvider
    brave: BraveFactory
    web: WebReader
    fetcher: WebFetcher


@dataclass(frozen=True)
class PublishingProviders:
    """Documents produits par l'application : PDF de nos gabarits HTML (leçons, programme, CV)
    par Gotenberg (D89), mise en page d'un CV importé et polices libres de ses gabarits (D119)."""

    html_pdf: HtmlPdfRenderer
    layout: PdfLayoutExtractor
    fonts: FontSource
