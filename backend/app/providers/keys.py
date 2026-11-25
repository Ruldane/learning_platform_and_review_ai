"""What the key screen expects from a key-based provider: a name, a label and a test.

`LlmProvider` already satisfies it; so does Brave (`search/brave.py`), without being an LLM
provider: the model list and the factory see none of it (D73)."""

from typing import Protocol

from app.providers.llm.base import KeyTestResult

__all__ = ["KeyProvider", "KeyTestResult"]


class KeyProvider(Protocol):
    name: str
    label: str

    async def test_key(self, api_key: str) -> KeyTestResult:
        """Check the key without raising; the message is in English and never quotes the key."""
        ...
