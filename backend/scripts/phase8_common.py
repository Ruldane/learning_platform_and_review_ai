"""Matériel commun des étapes du contrôle de la phase 8 (`check_phase8`) : l'état d'un passage
(`Track`), l'attente d'une condition avec son délai, l'heure locale de January et la garde des
réglages (remis comme avant, quoi qu'il arrive). Rien de ce qui est envoyé ou reçu n'apparaît dans
un message d'échec ni dans la sortie : seulement des étapes, des nombres, des codes et des
identifiants."""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_steps import cost_of as cost_of
from scripts.phase7_common import count_calls as count_calls
from scripts.phase7_common import llm_calls as llm_calls

POLL_S = 3.0  # un relevé dure des minutes : inutile d'interroger plus vite (les tests le règlent)


@dataclass
class Track:
    """Ce que les étapes se passent : le relevé fini, le brief du jour, l'identifiant de l'élément
    « Brief du jour prêt » du fil d'activité (partie `planifie`)."""

    radar: dict[str, Any] = field(default_factory=dict)
    brief: dict[str, Any] = field(default_factory=dict)
    activity_id: str = ""


type Step = Callable[[Run, Track], Awaitable[None]]


def local_now(zone: str) -> datetime:
    """L'heure locale de January (les tests la figent)."""
    try:
        return datetime.now(ZoneInfo(zone))
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now().astimezone()


async def wait_for(
    run: Run, step: str, ready: Callable[[], Awaitable[bool]], what: str, seconds: float
) -> None:
    """Attend que `ready()` soit vrai, au plus `seconds` (sans dépasser le délai total du
    passage) ; sinon `CheckFailed` « délai dépassé : `what` »."""
    deadline = time.monotonic() + seconds
    while not await ready():
        now = time.monotonic()
        if now > deadline or now - run.started > run.timeout_s:
            raise CheckFailed(step, f"Délai dépassé : {what}.")
        await asyncio.sleep(POLL_S)


async def put_settings(run: Run, step: str, settings: dict[str, Any]) -> None:
    await expect_ok(run, step, "PUT", "/settings", json=settings)


@asynccontextmanager
async def settings_kept(run: Run, step: str) -> AsyncIterator[dict[str, Any]]:
    """Les réglages d'avant, remis à la sortie quoi qu'il arrive. Si la remise échoue pendant une
    autre erreur, celle-ci reste l'erreur rendue (la remise manquée est dite)."""
    original: dict[str, Any] = await expect_ok(run, step, "GET", "/settings")
    try:
        yield original
    except BaseException:
        try:
            await put_settings(run, step, original)
        except CheckFailed:
            print("    réglages non remis : à relire dans les réglages", flush=True)
        raise
    await put_settings(run, step, original)
