"""Fausse API (httpx `MockTransport`) qui note les appels, pour les étapes du contrôle de fin de
phase 5 : des réponses par `(méthode, chemin)`, fixes ou calculées."""

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from scripts.phase4_steps import Run
from scripts.phase5_steps import Etude
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


def quiz_view(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    kinds = ["qcm", "short", "code", "explain"] * 2
    questions = [
        {
            "id": f"q{n}",
            "rank": n,
            "type": kind,
            "prompt": "Énoncé",
            "code": "x = 1" if kind == "code" else None,
            # l'ordre des choix change d'un essai à l'autre
            "choices": ["B", "A", "C"] if kind == "qcm" else [],
        }
        for n, kind in enumerate(kinds, start=1)
    ]
    return {"status": "ready", "questions": questions, "attempts": attempts}


def graded(score: int, passed: bool) -> dict[str, Any]:
    results = [
        {
            "question_id": f"q{n}",
            "points": 1.0 if passed else 0.5,
            "correct_answer": "A" if n in (1, 5) else f"Réponse {n}",
            "explanation": "Parce que.",
            "feedback": "",
        }
        for n in range(1, 9)
    ]
    done = {"status": "graded", "score": score, "passed": passed, "results": results}
    return done | {"followup": None if passed else {"revision_tasks": [], "retry_on": None}}


def quiz_api(
    attempts: list[dict[str, Any]],
    second: dict[str, Any],
    *,
    retry_on: dict[str, str | None] | None = None,
) -> FakeApi:
    """Deux modules `m1` (quiz `z1`, ses `attempts`) et `m2` (quiz `z2`, sans tentative) ;
    `retry_on` : le nouvel essai attendu de chaque module ; `second` : la tentative qu'on envoie."""
    waiting = {"m1": None, "m2": None} | (retry_on or {})
    listed = [
        {"module_id": m, "quiz_id": f"z{m[1]}", "status": "ready", "retry_on": day}
        for m, day in waiting.items()
    ]
    routes: dict[tuple[str, str], Any] = {
        ("GET", "/settings"): {"timezone": "Europe/Paris"},
        ("GET", "/programs/p1/quizzes"): listed,
        ("GET", "/quizzes/z1/attempts/a0"): graded(35, False) | {"id": "a0"},
    }
    for module, quiz, mine in (("m1", "z1", attempts), ("m2", "z2", [])):
        routes |= {
            ("POST", f"/modules/{module}/quiz"): {"quiz_id": quiz},
            ("GET", f"/quizzes/{quiz}"): quiz_view(mine),
            ("POST", f"/quizzes/{quiz}/attempts"): {
                "attempt_id": f"a{quiz[1]}x",
                "session_id": "s",
            },
            ("GET", f"/quizzes/{quiz}/attempts/a{quiz[1]}x"): second,
        }
    return FakeApi(routes)


def etude() -> Etude:
    return Etude(lessons={"l1": "m1", "l2": "m2"}, lesson_id="l1")
