"""Matériel commun des étapes du contrôle de la phase 7 (`check_phase7`) : l'état d'un passage
(`Track`), l'envoi d'une requête dont l'erreur HTTP est une réponse attendue (409, 422), le jour de
January (son fuseau, lu dans ses réglages) et le sondage d'une session. Rien de ce qui est envoyé
ou reçu n'apparaît dans un message d'échec ni dans la sortie : seulement des étapes, des nombres,
des codes et des identifiants."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from scripts.phase4_steps import API, CheckFailed, Run, expect_ok
from scripts.phase6_steps import wait_session as wait_session

COMPANY = "Société Fictive"
MANUAL_TITLE = "Développeuse IA (H/F)"  # la fiche manuelle du doublon probable (arbitrage P11)
MANUAL_URL = "https://offres.example.org/controle-phase-7/developpeuse-ia"


@dataclass
class Track:
    """Ce que les étapes se passent : l'offre et la version de CV de la phase 6, la fiche née de
    l'offre, la fiche manuelle, celle de la phrase et celle de la relance."""

    posting: dict[str, Any] = field(default_factory=dict)
    version: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    application_id: str = ""
    manual_id: str = ""
    intake_id: str = ""
    reminder_app_id: str = ""


type Step = Callable[[Run, Track], Awaitable[None]]


async def send(run: Run, step: str, method: str, path: str, **kwargs: Any) -> httpx.Response:
    """La réponse, quel que soit son code (les refus 409 et 422 sont des réponses attendues) ;
    seule une panne réseau est un échec."""
    try:
        return await run.client.request(method, f"{API}{path}", **kwargs)
    except httpx.HTTPError as exc:
        raise CheckFailed(step, f"API injoignable ({type(exc).__name__}).") from None


def code_of(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["code"])
    except (ValueError, KeyError, TypeError):
        return "sans code"


def details_of(response: httpx.Response) -> dict[str, Any]:
    try:
        details = response.json()["error"]["details"]
    except (ValueError, KeyError, TypeError):
        return {}
    return details if isinstance(details, dict) else {}


def expect_refusal(response: httpx.Response, step: str, label: str, status: int, code: str) -> None:
    """Échec si la réponse n'est pas le refus `status` / `code` attendu."""
    if response.status_code != status or code_of(response) != code:
        raise CheckFailed(
            step, f"{label} : HTTP {response.status_code} ({code_of(response)}), {status} attendu."
        )


def parse_day(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


async def today_of(run: Run, step: str) -> date:
    """Le jour de January : le fuseau de ses réglages, sinon la date locale."""
    settings = await expect_ok(run, step, "GET", "/settings")
    try:
        return datetime.now(ZoneInfo(str(settings["timezone"]))).date()
    except (KeyError, ZoneInfoNotFoundError, ValueError):
        return date.today()


async def first_delay(run: Run, step: str) -> int:
    """Le délai de la première relance (jours), 7 par défaut."""
    settings = await expect_ok(run, step, "GET", "/settings")
    delays = settings.get("reminder_delays_days") or [7]
    return int(delays[0])


def count_calls(events: list[dict[str, Any]]) -> int:
    """Les appels du modèle d'une session : un événement `cost.updated` par appel."""
    return sum(1 for event in events if event["type"] == "cost.updated")


async def llm_calls(run: Run, session_id: str) -> int:
    return count_calls(await run.events(session_id))
