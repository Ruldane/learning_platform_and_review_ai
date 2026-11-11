"""Embedder déterministe, sans réseau : tests et démonstration de bout en bout (comme
`FakeLlmProvider`). Les mots partagés rapprochent les textes ; ce n'est pas de la sémantique."""

import hashlib
import math
import re

_WORD = re.compile(r"\w+")


class HashingEmbedder:
    def __init__(self, dimension: int = 64) -> None:
        self._dimension = dimension

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def aembed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for word in _WORD.findall(text.lower()):
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:8], "big") % self._dimension] += 1.0
        norm = math.sqrt(sum(x * x for x in vector))
        return [x / norm for x in vector] if norm else vector
