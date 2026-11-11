"""Port des embeddings : sous-ensemble asynchrone de `langchain_core.embeddings.Embeddings`, pour
qu'une implémentation LangChain reste substituable sans que les features en dépendent."""

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
