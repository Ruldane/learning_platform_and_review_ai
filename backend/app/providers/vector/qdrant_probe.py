"""Sonde de Qdrant : `GET /readyz` (Qdrant >= 1.5, toujours accessible, même avec une clé d'API)."""

import httpx

from app.providers.health import HealthStatus, available, unexpected_status


class QdrantProbe:
    name = "qdrant"

    def __init__(self, url: str, http: httpx.AsyncClient) -> None:
        self._url = url.rstrip("/")
        self._http = http

    async def check(self) -> HealthStatus:
        response = await self._http.get(f"{self._url}/readyz")
        return available() if response.status_code == 200 else unexpected_status(response)
