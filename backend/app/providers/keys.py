"""Ce que l'écran des clés attend d'un fournisseur à clé : un nom, un libellé et un test.

`LlmProvider` le satisfait déjà ; Brave aussi (`search/brave.py`), sans être un fournisseur LLM :
la liste des modèles et la fabrique n'en voient rien (D73)."""

from typing import Protocol

from app.providers.llm.base import KeyTestResult

__all__ = ["KeyProvider", "KeyTestResult"]


class KeyProvider(Protocol):
    name: str
    label: str

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Vérifie la clé sans jamais lever ; le message est en français et ne cite pas la clé."""
        ...
