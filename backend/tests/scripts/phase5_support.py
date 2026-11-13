"""Matériel du contrôle de fin de phase 5, partie « tout », contre l'application réelle : le
programme semé calé sur la vraie date du jour, une page lisible pour la capture, et le planificateur
appelé directement quand le contrôle règle l'heure du bilan (la tâche réelle passe toutes les 15
minutes ; ici aucune horloge ni planificateur ne tourne). Aucun réseau ni LLM."""

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.core.providers import MemoryProviders
from app.db.models.program import Task, Week
from app.features.replan.service.weekly import run_weekly_reviews
from app.providers.web.base import WebDocument
from scripts import phase5_weekly
from scripts.phase5_capture import READABLE_URL
from tests.features.program.support import MONDAY
from tests.features.study.conftest import Seeded
from tests.support.memory import FakeWebReader

ZONE = ZoneInfo("Europe/Paris")
WEEKLY_AT = time(18, 30)  # dimanche, 18 h 30 à Paris : une demi-heure après l'heure du bilan
PAGE = (
    "Le tutoriel Python explique les listes, les dictionnaires et les compréhensions de liste, "
    "avec des exemples courts pour chaque notion."
)


# Jours (depuis le lundi de la semaine 1) des tâches du premier module qui restent à faire.
FIRST_MODULE_DAYS = {
    "Lire le chapitre 3": 0,
    "Lire le chapitre 4": 1,
    "Lire le chapitre 5": 2,
    "Pratiquer les bases": 2,
    "Faire le quiz 1": 3,
}


async def rebase_program(s: Seeded) -> date:
    """Le programme semé calé sur la vraie date, pour que la replanification de la semaine ait du
    travail quel que soit le jour du test : la semaine 1 est celle de lundi prochain (donc la
    « semaine en cours » du Stratège, plafonnée à 255 minutes : 425 minutes y sont prévues) et la
    semaine 2 la suivante. Le bloc du jour reste dû maintenant : seules deux lectures (hier et
    aujourd'hui) sont avant la semaine 1, la session les coche. Rend le lundi de la semaine 1."""
    today = datetime.now(ZONE).date()
    monday = today - timedelta(days=today.weekday()) + timedelta(days=7)
    shift = timedelta(days=(monday - MONDAY).days)
    async with s.rt.session_factory() as db:
        for week in (await db.execute(select(Week))).scalars():
            week.start_date += shift
        for task in (await db.execute(select(Task))).scalars():
            if task.title == "Lire le chapitre 1":
                task.planned_date = today - timedelta(days=1)
            elif task.title == "Lire le chapitre 2":
                task.planned_date = today
            elif task.title in FIRST_MODULE_DAYS:
                task.planned_date = monday + timedelta(days=FIRST_MODULE_DAYS[task.title])
            else:
                task.planned_date += shift
        await db.commit()
    return monday


def readable_page(memory: MemoryProviders) -> None:
    """Le lien lisible du contrôle rend une page ; tout autre lien (`example.invalid`) est
    illisible, comme sur le web."""
    reader = memory.web
    assert isinstance(reader, FakeWebReader)
    reader.pages[READABLE_URL] = WebDocument(
        READABLE_URL, "Tutoriel Python", PAGE, None, None, "fr", None
    )


def freeze_weekly_clock(monkeypatch: pytest.MonkeyPatch, monday: date) -> datetime:
    """L'heure locale du contrôle figée au dimanche qui finit la semaine 1 : la semaine relue est
    la semaine 1 et il reste la suivante, quel que soit le vrai jour. Rend cet instant."""
    sunday = datetime.combine(monday + timedelta(days=6), WEEKLY_AT, tzinfo=ZONE)
    monkeypatch.setattr(phase5_weekly, "local_now", lambda zone: sunday.astimezone(ZoneInfo(zone)))
    monkeypatch.setattr(phase5_weekly, "POLL_WEEKLY_S", 0.05)
    return sunday


async def weekly_scheduler(client: httpx.AsyncClient, app: FastAPI, at: datetime) -> None:
    """Joue la tâche `weekly_review` une fois, quand le contrôle a réglé l'heure du bilan (le
    réglage n'est plus celui par défaut) : le planificateur est appelé directement."""
    while True:
        saved = (await client.get("/api/v1/settings")).json()["weekly_review"]
        if saved != {"day": "sunday", "time": "18:00"}:
            await run_weekly_reviews(
                app.state.session_factory, app.state.replan, at.astimezone(UTC)
            )
            return
        await asyncio.sleep(0.05)
