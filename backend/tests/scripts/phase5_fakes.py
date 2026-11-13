"""Fausse API (httpx `MockTransport`) qui note les appels, pour les étapes du contrôle de fin de
phase 5 : des réponses par `(méthode, chemin)`, fixes ou calculées."""

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from scripts.phase4_steps import Run
from tests.scripts.phase4_fakes import no_events


@dataclass
class FakeApi:
    """`routes` : `(méthode, chemin)` -> JSON, ou fonction de la requête (réponse JSON ou
    `httpx.Response`) ; `calls` : `(méthode, chemin, corps)` dans l'ordre."""

    routes: dict[tuple[str, str], Any]
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api/v1")
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, path, body))
        found = self.routes.get((request.method, path))
        if found is None:
            return httpx.Response(404, json={"error": {"code": "not_found"}})
        value = found(request) if callable(found) else found
        return value if isinstance(value, httpx.Response) else httpx.Response(200, json=value)

    def run(self, timeout_s: float = 5.0) -> tuple[httpx.AsyncClient, Run]:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(self.handle), base_url="http://api"
        )
        return client, Run(client, no_events, timeout_s, program_id="p1")

    def sent(self, method: str, path: str) -> list[Any]:
        return [body for m, p, body in self.calls if (m, p) == (method, path)]
