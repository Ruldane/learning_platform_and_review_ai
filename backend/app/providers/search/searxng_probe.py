"""SearXNG probe: `GET /healthz` (route confirmed in `searx/webapp.py`), then once per probe
instance `GET /search?q=tremplin&format=json`. SearXNG answers 403 if the JSON format is not in
`search.formats` of `settings.yml`."""

import httpx

from app.providers.health import HealthStatus, available, unexpected_status

_JSON_REFUSED = "SearXNG may have JSON output disabled or may have rate-limited the request."
# The first real search may exceed the shared client's 3 s deadline: the JSON check
# has its own. `timeout` is the cap requested from the health service (probe + search);
# the check only happens once it has succeeded, after which only the `/healthz` probe runs.
_DEEP_TIMEOUT_SECONDS = 10.0
_CHECK_TIMEOUT_SECONDS = _DEEP_TIMEOUT_SECONDS + 5.0


class SearxngProbe:
    name = "searxng"
    timeout = _CHECK_TIMEOUT_SECONDS

    def __init__(self, url: str, http: httpx.AsyncClient) -> None:
        self._url = url.rstrip("/")
        self._http = http
        self._json_verified = False

    async def _check_json(self) -> HealthStatus:
        response = await self._http.get(
            f"{self._url}/search",
            params={"q": "tremplin", "format": "json"},
            timeout=_DEEP_TIMEOUT_SECONDS,
        )
        if response.status_code == 403:
            return HealthStatus(ok=False, detail=_JSON_REFUSED)
        if response.status_code != 200:
            return unexpected_status(response)
        self._json_verified = True
        return available()

    async def check(self) -> HealthStatus:
        response = await self._http.get(f"{self._url}/healthz")
        if response.status_code != 200:
            return unexpected_status(response)
        return available() if self._json_verified else await self._check_json()
