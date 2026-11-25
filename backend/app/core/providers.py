"""External services as the features receive them. Data only: building the concrete
implementations lives in `app/bootstrap.py`."""

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
from app.providers.sandbox.base import CodeSandbox
from app.providers.search.base import SearchProvider
from app.providers.storage.base import FileStorage
from app.providers.vector.base import MemoryRepository
from app.providers.web.base import WebFetcher, WebReader, YoutubeTranscripts


@dataclass
class Providers:
    """LLM providers, factory, encryptor, `.env` keys, providers of the key screen (LLM and Brave),
    health checks, OpenID Connect connection (`None` in local mode), progress of the embeddings
    model (`GET /health/embedding`, P13) and the code execution sandbox (`CodeSandbox`, set by
    `bootstrap_ide`; `None` before composition)."""

    llm: Mapping[str, LlmProvider]
    llm_factory: LlmFactory
    cipher: Cipher
    env_keys: Mapping[str, str | None]
    key_providers: Mapping[str, KeyProvider]
    health_checks: list[HealthCheck] = field(default_factory=list)
    oidc: OidcProvider | None = None
    embedding: EmbeddingProgressSource | None = None
    sandbox: CodeSandbox | None = None


@dataclass(frozen=True)
class MemoryProviders:
    """Memory services: vectorization, vector index, storage of imported files, PDF extraction,
    safe web reading and YouTube transcripts."""

    embedder: Embedder
    index: MemoryRepository
    storage: FileStorage
    pdf: PdfTextExtractor
    web: WebReader
    youtube: YoutubeTranscripts


# User's Brave key → Brave client: the key is read at each search (D73).
BraveFactory = Callable[[str], SearchProvider]


@dataclass(frozen=True)
class ResearchProviders:
    """Web search services: SearXNG (no key), Brave factory, the memory web reader (the same object
    as `MemoryProviders.web`) and a safe fetcher (SSRF guard) for the local copies of the free
    PDFs of the resources (D91)."""

    searxng: SearchProvider
    brave: BraveFactory
    web: WebReader
    fetcher: WebFetcher


@dataclass(frozen=True)
class PublishingProviders:
    """Documents produced by the application: PDF of our HTML templates (lessons, program, CV)
    through Gotenberg (D89), layout of an imported CV and free fonts of its templates (D119)."""

    html_pdf: HtmlPdfRenderer
    layout: PdfLayoutExtractor
    fonts: FontSource
