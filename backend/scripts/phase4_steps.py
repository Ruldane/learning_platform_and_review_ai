"""Étapes longues du contrôle de fin de phase 4 (`check_phase4`) : le contexte d'un passage (`Run` :
client, délai, identifiants), la lecture des événements par WebSocket, puis le cadrage, le
Conseil, le programme et les leçons. Aucun texte reçu ou envoyé n'apparaît dans un message
d'échec : seulement des étapes, des nombres, des codes et des identifiants."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from websockets.asyncio.client import connect

API = "/api/v1"
POLL_S = 0.25
FEED_TIMEOUT_S = 60.0
MAX_FRAMING_QUESTIONS = 5
FRAMING_ANSWER = "Environ huit heures par semaine, surtout le soir ; un peu de Python."
MIN_SCORED_SOURCES = 8
DEBATERS = frozenset({"strategist", "practitioner", "scout", "skeptic"})
LESSON_WEEKS = (1, 2)
MIN_RESOURCES, MAX_RESOURCES = 3, 6

type EventFeed = Callable[[str], Awaitable[list[dict[str, Any]]]]


class CheckFailed(Exception):
    """Étape ratée : `step` et un message en français (jamais une donnée de January)."""

    def __init__(self, step: str, message: str) -> None:
        super().__init__(message)
        self.step = step


def _error_code(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["code"])
    except (ValueError, KeyError, TypeError):
        return "sans code"


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
    week_ranks: list[int] = field(default_factory=list)

    async def request(self, step: str, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self.client.request(method, f"{API}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise CheckFailed(step, f"API injoignable ({type(exc).__name__}).") from None
        if response.is_error:
            code = _error_code(response)
            raise CheckFailed(step, f"{method} {path} : HTTP {response.status_code} ({code}).")
        return response

    async def until(self, step: str, ready: Callable[[], Awaitable[bool]], what: str) -> None:
        """Attend que `ready()` soit vrai, dans le délai total du passage."""
        while not await ready():
            if time.monotonic() - self.started > self.timeout_s:
                raise CheckFailed(step, f"Délai dépassé : {what}.")
            await asyncio.sleep(POLL_S)


async def expect_ok(run: Run, step: str, method: str, path: str, **kwargs: Any) -> Any:
    return (await run.request(step, method, path, **kwargs)).json()


def websocket_feed(client: httpx.AsyncClient) -> EventFeed:
    """Événements d'une session jusqu'au dernier écrit (`last_seq`), lus par son WebSocket."""

    async def events(session_id: str) -> list[dict[str, Any]]:
        view = (await client.get(f"{API}/sessions/{session_id}")).json()
        last = int(view["last_seq"])
        base = client.base_url
        scheme = "wss" if base.scheme == "https" else "ws"
        url = base.copy_with(scheme=scheme, path=f"{API}/sessions/{session_id}/stream")
        found: list[dict[str, Any]] = []
        if last == 0:
            return found
        async with asyncio.timeout(FEED_TIMEOUT_S), connect(str(url)) as socket:
            async for raw in socket:
                found.append(json.loads(raw))
                if int(found[-1]["seq"]) >= last:
                    break
        return found

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


def debate_rounds_of(events: list[dict[str, Any]]) -> dict[int, set[str]]:
    """Débatteurs qui ont parlé à chaque tour (étape `positions` = tour 1, `tour-N` = tour N)."""
    steps: dict[str, str] = {}
    rounds: dict[int, set[str]] = {}
    for event in events:
        agent = event.get("agent") or ""
        if event["type"] == "agent.started":
            steps[agent] = event["payload"]["step"]
        elif event["type"] == "agent.message" and agent in DEBATERS:
            step = steps.get(agent, "")
            number = 1 if step == "positions" else int(step[5:]) if step[5:].isdigit() else 0
            if number:
                rounds.setdefault(number, set()).add(agent)
    return rounds


def _check_debate(events: list[dict[str, Any]], debate_rounds: int) -> None:
    rounds = debate_rounds_of(events)
    if not 2 <= len(rounds) <= 1 + debate_rounds:
        raise CheckFailed("conseil", f"{len(rounds)} tour(s) de débat (réglage : {debate_rounds}).")
    partial = sorted(n for n, agents in rounds.items() if agents != DEBATERS)
    if partial:
        raise CheckFailed("conseil", f"Tours incomplets (4 débatteurs attendus) : {partial}.")


async def check_council(run: Run) -> None:
    await wait_question(run, "conseil", run.council_id, "choose_path")
    events = await run.events(run.council_id)
    found = [e["payload"] for e in events if e["type"] == "source.found"]
    scored = {p.get("source_id") or p["url"] for p in found if p.get("score") is not None}
    if len(scored) < MIN_SCORED_SOURCES:
        raise CheckFailed("conseil", f"{len(scored)} source(s) notée(s) : 8 au moins.")
    settings = await expect_ok(run, "conseil", "GET", "/settings")
    _check_debate(events, int(settings["debate_rounds"]))
    if not any(e["type"] == "board.update" for e in events):
        raise CheckFailed("conseil", "Aucun tableau dessiné (board.update).")
    ready = sum(e["type"] == "proposal.ready" for e in events)
    if not 2 <= ready <= 3:
        raise CheckFailed("conseil", f"{ready} proposition(s) : 2 à 3 attendues.")


def _week_problems(week: dict[str, Any], cap: int) -> list[str]:
    tasks = [task for module in week["modules"] for task in module["tasks"]]
    rank = week["rank"]
    problems: list[str] = []
    if week["load_minutes"] > cap:
        problems.append(f"semaine {rank} : {week['load_minutes']} min pour {cap} au plus")
    if not any(task["type"] == "pratiquer" for task in tasks):
        problems.append(f"semaine {rank} sans pratique")
    last_day = max((task["planned_date"] for task in tasks), default=None)
    if not any(t["type"] == "quiz" and t["planned_date"] == last_day for t in tasks):
        problems.append(f"semaine {rank} ne finit pas par un quiz")
    return problems


async def check_program(run: Run) -> None:
    async def planned() -> bool:
        goal = await expect_ok(run, "programme", "GET", f"/goals/{run.goal_id}")
        run.program_id = goal.get("program_id") or ""
        run.program_session_id = goal.get("program_session_id") or ""
        return bool(run.program_id and run.program_session_id)

    await run.until("programme", planned, "aucun programme lancé")
    await wait_question(run, "programme", run.program_session_id, "validate_program")
    program = await expect_ok(run, "programme", "GET", f"/programs/{run.program_id}")
    if program["status"] != "draft" or not program["weeks"]:
        raise CheckFailed("programme", f"Programme {program['status']}, sans brouillon à valider.")
    problems = [p for w in program["weeks"] for p in _week_problems(w, program["cap_minutes"])]
    if problems:
        raise CheckFailed("programme", f"Règles du programme non tenues : {'; '.join(problems)}.")
    run.week_ranks = [week["rank"] for week in program["weeks"]]


async def _lesson_ready(run: Run, lesson: dict[str, Any]) -> None:
    pdf = await run.request("leçons", "GET", f"/lessons/{lesson['id']}/pdf")
    if not pdf.content.startswith(b"%PDF"):
        raise CheckFailed("leçons", f"Leçon {lesson['id']} : le PDF n'en est pas un.")
    detail = await expect_ok(run, "leçons", "GET", f"/lessons/{lesson['id']}")
    count = len(detail["resources"])
    if not MIN_RESOURCES <= count <= MAX_RESOURCES:
        raise CheckFailed(
            "leçons", f"Leçon {lesson['id']} : {count} ressource(s), 3 à 6 attendues."
        )


async def check_lessons(run: Run) -> None:
    weeks = [rank for rank in LESSON_WEEKS if rank in run.week_ranks]
    lessons: list[dict[str, Any]] = []

    async def produced() -> bool:
        found = await expect_ok(run, "leçons", "GET", f"/programs/{run.program_id}/lessons")
        lessons[:] = [lesson for lesson in found if lesson["week_rank"] in weeks]
        failed = [lesson["id"] for lesson in lessons if lesson["status"] == "failed"]
        if failed:
            raise CheckFailed("leçons", f"Leçon(s) en échec : {', '.join(failed)}.")
        covered = {lesson["week_rank"] for lesson in lessons}
        # Une leçon est rangée « prête » puis son PDF est rendu : on attend les deux.
        done = all(lesson["status"] == "ready" and lesson["pdf_available"] for lesson in lessons)
        return covered == set(weeks) and done

    await run.until("leçons", produced, "leçons des semaines 1 et 2 jamais prêtes avec leur PDF")
    for lesson in lessons:
        await _lesson_ready(run, lesson)
