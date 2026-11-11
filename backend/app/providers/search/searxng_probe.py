"""Sonde de SearXNG : `GET /healthz` (route confirmée dans `searx/webapp.py`), puis une seule
fois par instance de sonde `GET /search?q=tremplin&format=json`. SearXNG répond 403 si le format
JSON n'est pas dans `search.formats` de `settings.yml`."""

import httpx

from app.providers.health import HealthStatus, available, unexpected_status

_JSON_DISABLED = "Le format JSON n'est pas activé dans SearXNG."


class SearxngProbe:
    name = "searxng"

    def __init__(self, url: str, http: httpx.AsyncClient) -> None:
        self._url = url.rstrip("/")
        self._http = http
        self._json_verified = False

    async def _check_json(self) -> HealthStatus:
        response = await self._http.get(
            f"{self._url}/search", params={"q": "tremplin", "format": "json"}
        )
        if response.status_code == 403:
            return HealthStatus(ok=False, detail=_JSON_DISABLED)
        if response.status_code != 200:
            return unexpected_status(response)
        self._json_verified = True
        return available()

    async def check(self) -> HealthStatus:
        response = await self._http.get(f"{self._url}/healthz")
        if response.status_code != 200:
            return unexpected_status(response)
        return available() if self._json_verified else await self._check_json()
