"""Port des embeddings : sous-ensemble asynchrone de `langchain_core.embeddings.Embeddings`, pour
qu'une implémentation LangChain reste substituable sans que les features en dépendent."""

from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError


class Embedder(Protocol):
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def aembed_query(self, text: str) -> list[float]: ...


class EmbeddingsUnavailable(AppError):
    """Ollama injoignable, trop lent, modèle absent ou réponse inexploitable."""

    def __init__(self) -> None:
        super().__init__(
            "embeddings_unavailable",
            "Le service d'embeddings (Ollama) est indisponible ou le modèle bge-m3 "
            "n'est pas encore téléchargé.",
            status_code=503,
        )


@dataclass(frozen=True)
class EmbeddingProgressData:
    """État du modèle d'embeddings : présent, ou en cours de téléchargement (`percent` de 0 à 99
    tant qu'il n'est pas là, 100 quand il l'est, `None` tant que la taille n'est pas connue).
    `detail` est un texte français sans donnée personnelle."""

    model: str
    present: bool
    percent: int | None
    detail: str


class EmbeddingProgressSource(Protocol):
    """Ce que `GET /health/embedding` lit : l'état du modèle, et le téléchargement s'il manque."""

    async def progress(self) -> EmbeddingProgressData: ...
