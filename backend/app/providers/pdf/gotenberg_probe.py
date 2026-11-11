"""Sonde de Gotenberg : `GET /health` (200 si Chromium et LibreOffice répondent, 503 sinon)."""

import httpx

from app.providers.health import HealthStatus, available, unexpected_status


class GotenbergProbe:
    name = "gotenberg"

    def __init__(self, url: str, http: httpx.AsyncClient) -> None:
        self._url = url.rstrip("/")
        self._http = http

    async def check(self) -> HealthStatus:
        response = await self._http.get(f"{self._url}/health")
        return available() if response.status_code == 200 else unexpected_status(response)
