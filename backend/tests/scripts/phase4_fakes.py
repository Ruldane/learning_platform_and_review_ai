"""Fausse API (httpx `MockTransport`) et données fabriquées pour tester les étapes du contrôle
de fin de phase 4 une à une, sans application ni réseau."""

from collections.abc import Callable
from typing import Any

import httpx

from scripts.phase4_steps import Run

type Route = Callable[[httpx.Request], httpx.Response]


def week(rank: int, *, module: str | None = None, load: int = 200, **kinds: str) -> dict[str, Any]:
    """Une semaine d'un module : lecture lundi, pratique mercredi, quiz vendredi (dates fictives
    dont l'ordre suffit). `kinds` remplace le type d'une tâche (`practice="lire"`, …)."""
    tasks = [
        {"type": kinds.get("reading", "lire"), "planned_date": f"2026-12-0{rank}-1"},
        {"type": kinds.get("practice", "pratiquer"), "planned_date": f"2026-12-0{rank}-3"},
        {"type": kinds.get("quiz", "quiz"), "planned_date": f"2026-12-0{rank}-5"},
    ]
    modules = [{"id": module or f"m{rank}", "tasks": tasks}]
    return {"rank": rank, "load_minutes": load, "modules": modules}


def program(*weeks: dict[str, Any], status: str = "draft", cap: int = 400) -> dict[str, Any]:
    return {"id": "p1", "status": status, "cap_minutes": cap, "weeks": list(weeks)}


def lesson(
    module: str, status: str = "ready", pdf: bool = True, attempts: int = 3
) -> dict[str, Any]:
    """Une leçon de `GET /programs/{id}/lessons` ; `attempts` à 3 par défaut : une leçon
    `failed` a épuisé ses essais (D98)."""
    return {
        "id": f"l-{module}",
        "module_id": module,
        "status": status,
        "attempts": attempts,
        "pdf_available": pdf,
    }


def json_api(routes: dict[str, Any]) -> Route:
    """Répond le JSON de la première route dont le chemin finit par la clé ; une valeur
    appelable reçoit la requête (réponses qui changent d'un appel à l'autre)."""

    def handle(request: httpx.Request) -> httpx.Response:
        for suffix, value in routes.items():
            if request.url.path.endswith(suffix):
                found = value(request) if callable(value) else value
                if isinstance(found, httpx.Response):
                    return found
                return httpx.Response(200, json=found)
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    return handle


def api(routes: dict[str, Any]) -> httpx.AsyncClient:
    """Client de la fausse API (`json_api`)."""
    return httpx.AsyncClient(transport=httpx.MockTransport(json_api(routes)), base_url="http://api")


async def no_events(session_id: str) -> list[dict[str, Any]]:
    return []


def fake_run(client: httpx.AsyncClient, *, timeout_s: float = 5.0) -> Run:
    return Run(client, no_events, timeout_s, goal_id="g1", program_id="p1")
