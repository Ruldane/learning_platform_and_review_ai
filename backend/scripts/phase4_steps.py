"""Étapes longues du contrôle de fin de phase 4 (`check_phase4`) : le contexte d'un passage (`Run` :
client, délai, identifiants), la lecture des événements par WebSocket, puis le cadrage, le
Conseil, le programme et les leçons. Les règles elles-mêmes sont dans `phase4_rules`. Aucun texte
reçu ou envoyé n'apparaît dans un message d'échec : seulement des étapes, des nombres, des codes
et des identifiants."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from scripts.phase4_rules import (
    CheckFailed,
    check_council_events,
    check_lesson_files,
    check_program_draft,
    lessons_done,
)

API = "/api/v1"
POLL_S = 0.25
FEED_TIMEOUT_S = 60.0
MAX_FRAMING_QUESTIONS = 5
FRAMING_ANSWER = "Environ huit heures par semaine, surtout le soir ; un peu de Python."

type EventFeed = Callable[[str], Awaitable[list[dict[str, Any]]]]

__all__ = ["API", "CheckFailed", "EventFeed", "Run", "expect_ok", "websocket_feed"]


def _error_code(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["code"])
    except (ValueError, KeyError, TypeError):
        return "sans code"


async def _request(
    client: httpx.AsyncClient, step: str, method: str, path: str, **kwargs: Any
) -> httpx.Response:
    try:
        response = await client.request(method, f"{API}{path}", **kwargs)
    except httpx.HTTPError as exc:
        raise CheckFailed(step, f"API injoignable ({type(exc).__name__}).") from None
    if response.is_error:
        code = _error_code(response)
        raise CheckFailed(step, f"{method} {path} : HTTP {response.status_code} ({code}).")
    return response


@dataclass
class Run:
    client: httpx.AsyncClient
    events: EventFeed
    timeout_s: float
    started: float = field(default_factory=time.monotonic)
    goal_id: str = ""
    council_id: str = ""
    program_id: str = ""
    program_session_id: str = ""
    # Modules des semaines 1 et 2 (id -> rang) : chacun doit avoir sa leçon prête avec son PDF.
    lesson_modules: dict[str, int] = field(default_factory=dict)

    async def request(self, step: str, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await _request(self.client, step, method, path, **kwargs)

    async def until(self, step: str, ready: Callable[[], Awaitable[bool]], what: str) -> None:
        """Attend que `ready()` soit vrai, dans le délai total du passage."""
        while not await ready():
            if time.monotonic() - self.started > self.timeout_s:
                raise CheckFailed(step, f"Délai dépassé : {what}.")
            await asyncio.sleep(POLL_S)


async def expect_ok(run: Run, step: str, method: str, path: str, **kwargs: Any) -> Any:
    return (await run.request(step, method, path, **kwargs)).json()


async def _read_stream(step: str, url: str, last: int) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    async with asyncio.timeout(FEED_TIMEOUT_S), connect(url) as socket:
        async for raw in socket:
            found.append(json.loads(raw))
            if int(found[-1]["seq"]) >= last:
                return found
    raise CheckFailed(step, f"Flux fermé après {len(found)} événement(s) sur {last}.")


def websocket_feed(client: httpx.AsyncClient, step: str = "conseil") -> EventFeed:
    """Événements d'une session jusqu'au dernier écrit (`last_seq`), lus par son WebSocket.
    Toute erreur réseau ou fermeture anticipée du flux devient un `CheckFailed` de `step`."""

    async def events(session_id: str) -> list[dict[str, Any]]:
        view = (await _request(client, step, "GET", f"/sessions/{session_id}")).json()
        last = int(view["last_seq"])
        if last == 0:
            return []
        base = client.base_url
        scheme = "wss" if base.scheme == "https" else "ws"
        url = base.copy_with(scheme=scheme, path=f"{API}/sessions/{session_id}/stream")
        try:
            return await _read_stream(step, str(url), last)
        except TimeoutError:
            raise CheckFailed(step, "Flux d'événements muet (délai dépassé).") from None
        except (OSError, WebSocketException) as exc:
            raise CheckFailed(
                step, f"Flux d'événements injoignable ({type(exc).__name__})."
            ) from None

    return events


async def wait_question(run: Run, step: str, session_id: str, kind: str) -> dict[str, Any]:
    """La question `kind` en attente de la session ; échec si la session s'arrête avant."""
    pending: dict[str, Any] = {}

    async def asked() -> bool:
        view = await expect_ok(run, step, "GET", f"/sessions/{session_id}")
        if view["status"] in ("failed", "cancelled", "completed"):
            code = (view.get("error") or {}).get("code", "aucun")
            raise CheckFailed(step, f"Session {session_id} arrêtée ({view['status']}, {code}).")
        question = view.get("pending_interrupt") or {}
        if view["status"] == "waiting_user" and question.get("kind") == kind:
            pending.update(question)
            return True
        return False

    await run.until(step, asked, f"question « {kind} » jamais posée")
    return pending


async def check_framing(run: Run) -> None:
    pending = await wait_question(run, "cadrage", run.council_id, "framing")
    fields = pending.get("fields", [])
    if len(fields) > MAX_FRAMING_QUESTIONS:
        raise CheckFailed("cadrage", f"{len(fields)} questions de cadrage : 5 au plus.")
    value = {"answers": {item["id"]: FRAMING_ANSWER for item in fields}}
    body = {"interrupt_id": pending["interrupt_id"], "value": value}
    await expect_ok(run, "cadrage", "POST", f"/sessions/{run.council_id}/resume", json=body)


async def check_council(run: Run) -> None:
    await wait_question(run, "conseil", run.council_id, "choose_path")
    events = await run.events(run.council_id)
    settings = await expect_ok(run, "conseil", "GET", "/settings")
    check_council_events(events, int(settings["debate_rounds"]))


async def check_program(run: Run) -> None:
    async def planned() -> bool:
        goal = await expect_ok(run, "programme", "GET", f"/goals/{run.goal_id}")
        run.program_id = goal.get("program_id") or ""
        run.program_session_id = goal.get("program_session_id") or ""
        return bool(run.program_id and run.program_session_id)

    await run.until("programme", planned, "aucun programme lancé")
    await wait_question(run, "programme", run.program_session_id, "validate_program")
    program = await expect_ok(run, "programme", "GET", f"/programs/{run.program_id}")
    run.lesson_modules = check_program_draft(program)


async def check_lessons(run: Run) -> None:
    """Chaque module des semaines 1 et 2 a sa leçon prête, avec son PDF et 3 à 6 ressources."""
    lessons: list[dict[str, Any]] = []

    async def produced() -> bool:
        found = await expect_ok(run, "leçons", "GET", f"/programs/{run.program_id}/lessons")
        lessons[:] = [lesson for lesson in found if lesson["module_id"] in run.lesson_modules]
        return lessons_done(lessons, run.lesson_modules)

    await run.until("leçons", produced, "leçons des semaines 1 et 2 jamais prêtes avec leur PDF")
    for lesson in lessons:
        pdf = await run.request("leçons", "GET", f"/lessons/{lesson['id']}/pdf")
        detail = await expect_ok(run, "leçons", "GET", f"/lessons/{lesson['id']}")
        check_lesson_files(lesson["id"], pdf.content, len(detail["resources"]))
