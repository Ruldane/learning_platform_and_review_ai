"""Fausse API (httpx `MockTransport`) du contrôle de la phase 8 : réglages, fil d'activité, brief du
jour, relevé du radar, sessions et pages d'offres, avec les réponses que le vrai back rend. Les
nombres d'interrogations avant qu'un élément n'apparaisse se règlent par partie. Aucun réseau."""

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest

from scripts.check_phase8 import CheckFailed, run_check

OFFER_PAGE = "https://jobs.example/offre-a"
OFFER_URLS = (OFFER_PAGE, "https://jobs.example/offre-b", "https://jobs.example/offre-c")
PAGES = {"/offre-a": "Salaire 45 à 55 k€ par an", "/offre-b": "Pas de chiffre", "/offre-c": "Texte"}
SETTINGS: dict[str, Any] = {
    "timezone": "Europe/Paris",
    "brief_time": "07:00",
    "radar_role": "",
    "radar_zone": "France",
    "vision_enabled": True,
}


def radar_run(**over: Any) -> dict[str, Any]:
    offers = [
        {
            "url": OFFER_URLS[0],
            "title": "Titre A",
            "company": "Maison A",
            "score": 82,
            "salary": "45-55 k€",
        },
        {
            "url": OFFER_URLS[1],
            "title": "Titre B",
            "company": "Maison B",
            "score": 74,
            "salary": None,
        },
        {
            "url": OFFER_URLS[2],
            "title": "Titre C",
            "company": "Maison C",
            "score": 40,
            "salary": None,
        },
    ]
    run = {
        "id": "r1",
        "status": "done",
        "error_code": None,
        "role": "Développeur Python",
        "zone": "Lyon",
        "read_count": 40,
        "blocked_count": 8,
        "not_postings": 4,
        "analyzed": 3,
        "not_analyzed": 33,
        "low_sample": False,
        "blocked_domains": [{"domain": "bloque.example", "count": 8}],
        "ranking": [{"skill": "Python", "count": 3, "share": 1.0, "rank": 1}],
        "offers": offers,
    }
    return run | over


def brief_json(**over: Any) -> dict[str, Any]:
    brief = {
        "id": "b1",
        "day": "2026-11-16",
        "origin": "opening",
        "block": {
            "module_title": "M",
            "lesson_id": "l1",
            "lesson_title": "L",
            "minutes": 45,
            "tasks": [],
        },
        "reviews": {"queue": 12, "remaining": 0},
        "reminders": {"due": 2, "items": [{"company": "X"}, {"company": "Y"}]},
        "offers": {
            "run_id": "r1",
            "items": [{"url": OFFER_URLS[0], "score": 82, "title": "T", "company": "C"}],
        },
        "week": {
            "planned_minutes": 600,
            "done_minutes": 120,
            "tasks_done": 3,
            "tasks_total": 9,
            "study_minutes": 120,
            "streak_days": 4,
        },
        "resource": {
            "title": "Un guide",
            "url": "https://docs.example/guide",
            "domain": "docs.example",
            "published": None,
            "why": "Pour le bloc du jour.",
        },
        "advice": ["Garde ton rythme de 4 jours.", "Révise tes 12 fiches avant la leçon."],
        "advice_status": "ready",
        "session_id": "s-brief",
    }
    return brief | over


class FakeApi:
    """L'API vue par le contrôle. `polls` : interrogations d'un élément avant qu'il n'apparaisse."""

    def __init__(self, *, polls: int = 2) -> None:
        self.settings = dict(SETTINGS)
        self.puts: list[dict[str, Any]] = []
        self.polls = polls
        self.activity: list[dict[str, Any]] = []
        self.brief: dict[str, Any] | None = None
        self.brief_over: dict[str, Any] = {}
        self.pending_gets = 0
        self.run: dict[str, Any] = radar_run()
        self.second_status = 409
        self.second_run_id = "r1"
        self.launched = False
        self.pages = dict(PAGES)
        self.seen: list[str] = []
        self._ticks = 0

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle), base_url="http://api")

    def create_brief(self, origin: str) -> dict[str, Any]:
        self.brief = brief_json(origin=origin) | self.brief_over
        self.activity = [
            {"id": f"brief:{self.brief['id']}:ready", "kind": "brief", "at": "2026-11-16T09:00:00Z"}
        ]
        return self.brief

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != "api":
            return self._page(request)
        path, method = request.url.path.removeprefix("/api/v1"), request.method
        self.seen.append(f"{method} {path}")
        found = self._route(request, path, method)
        return found if isinstance(found, httpx.Response) else httpx.Response(200, json=found)

    def _page(self, request: httpx.Request) -> httpx.Response:
        text = self.pages.get(request.url.path)
        return httpx.Response(200, text=text) if text is not None else httpx.Response(404)

    def _route(self, request: httpx.Request, path: str, method: str) -> Any:
        if path == "/settings":
            if method == "PUT":
                self.settings = json.loads(request.content)
                self.puts.append(self.settings)
            return self.settings
        if path == "/activity":
            return self._activity()
        if path == "/brief/today":
            return self._today()
        if path == "/radar/runs" and method == "POST":
            return self._launch(request)
        if path.startswith("/radar/runs/"):
            return self._radar_poll()
        if path == "/radar/latest":
            running = {"id": "r1"} if self.run["status"] == "running" else None
            return {"running": running, "latest": self.run if running is None else None}
        if path.startswith("/sessions/"):
            return {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0123, "last_seq": 0}
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    def _activity(self) -> dict[str, Any]:
        if self.settings["brief_time"] != SETTINGS["brief_time"] and self.brief is None:
            self._ticks += 1
            if self._ticks > self.polls:
                self.create_brief("schedule")
        return {"items": list(self.activity), "latest_at": None}

    def _today(self) -> dict[str, Any]:
        if self.brief is None:
            self.create_brief("opening")
        assert self.brief is not None
        if self.pending_gets > 0:
            self.pending_gets -= 1
            return self.brief | {"advice_status": "pending", "advice": None}
        return self.brief

    def _launch(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if self.launched:
            error = {"code": "radar_in_progress", "details": {"run_id": self.second_run_id}}
            if self.second_status == 202:
                return httpx.Response(202, json={"run_id": "r2", "session_id": "s2"})
            return httpx.Response(self.second_status, json={"error": error})
        self.launched = True
        self.settings |= {"radar_role": body["role"], "radar_zone": body["zone"]}
        return httpx.Response(202, json={"run_id": "r1", "session_id": "s-radar"})

    def _radar_poll(self) -> dict[str, Any]:
        self._ticks += 1
        if self._ticks <= self.polls:
            return self.run | {"status": "running"}
        return self.run


NOON = datetime(2026, 11, 16, 10, 0, 12, tzinfo=ZoneInfo("Europe/Paris"))
SENTENCES = ("Garde ton rythme de 4 jours.", "Révise tes 12 fiches avant la leçon.")


async def no_events(session_id: str) -> list[dict[str, Any]]:
    return [{"type": "cost.updated"}] * 3


async def play(fake: FakeApi, part: str, logs: str | None = "") -> list[str]:
    async with fake.client() as client:
        return await run_check(client, part=part, timeout_s=30, events=no_events, logs=logs)  # type: ignore[arg-type]


async def fails(fake: FakeApi, part: str, step: str, message: str, logs: str | None = "") -> None:
    with pytest.raises(CheckFailed) as failed:
        await play(fake, part, logs)
    assert failed.value.step == step
    assert message in str(failed.value)
