"""Contrôle de fin de phase 4 (SPEC 18.1) : un objectif mène à un programme validé avec les leçons
PDF de ses 2 premières semaines. Joué contre l'API en marche (Docker : SearXNG, Gotenberg et le
modèle réel ; tests : fournisseurs factices et modèles scriptés).

    uv run python -m scripts.check_phase4 --api http://localhost:8000

Neuf étapes, arrêt à la première ratée (`CheckFailed`, message en français, code de sortie 1).
Rien de ce qui est envoyé ou reçu n'est affiché : seulement les étapes, des nombres et des codes.
Les événements des sessions (sources notées, tours du débat, tableaux, propositions) se lisent par
le WebSocket de la session (`websocket_feed`)."""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from typing import Any

import httpx

from scripts.phase4_steps import (
    API,
    CheckFailed,
    EventFeed,
    Run,
    check_council,
    check_framing,
    check_lessons,
    check_program,
    expect_ok,
    websocket_feed,
)

STEPS = (
    "santé",
    "objectif",
    "cadrage",
    "conseil",
    "choix",
    "programme",
    "validation",
    "leçons",
    "exports",
)
REQUIRED_SERVICES = ("gotenberg", "searxng")
DEFAULT_GOAL = "Devenir AI product engineer"
HTTP_TIMEOUT_S = 60.0

__all__ = ["STEPS", "CheckFailed", "EventFeed", "main", "run_check"]


async def _health(run: Run) -> None:
    report = await expect_ok(run, "santé", "GET", "/health")
    checks: dict[str, Any] = report.get("checks", {})
    down = [name for name in REQUIRED_SERVICES if not checks.get(name, {}).get("ok")]
    if down:
        raise CheckFailed("santé", f"Service indisponible : {', '.join(down)}.")


async def _goal(run: Run, goal: str) -> None:
    started = await expect_ok(run, "objectif", "POST", "/goals", json={"text": goal})
    run.goal_id = started["goal"]["id"]
    run.council_id = started["session_id"]


async def _choose(run: Run) -> None:
    proposals = await expect_ok(run, "choix", "GET", f"/goals/{run.goal_id}/proposals")
    first = proposals[0]["id"]
    await expect_ok(run, "choix", "POST", f"/proposals/{first}/choose", json={})


async def _validate(run: Run) -> None:
    path = f"/programs/{run.program_id}"
    await expect_ok(run, "validation", "POST", f"{path}/validate")

    async def validated() -> bool:
        program = await expect_ok(run, "validation", "GET", path)
        return bool(program["status"] == "validated")

    await run.until("validation", validated, "programme jamais validé")


async def _exports(run: Run) -> None:
    path = f"/programs/{run.program_id}"
    pdf = await run.request("exports", "GET", f"{path}/export.pdf")
    if not pdf.content.startswith(b"%PDF"):
        raise CheckFailed("exports", "L'export PDF du programme n'est pas un PDF.")
    ics = await run.request("exports", "GET", f"{path}/export.ics")
    if "BEGIN:VCALENDAR" not in ics.text:
        raise CheckFailed("exports", "L'export .ics du programme n'est pas un calendrier.")


async def run_check(
    client: httpx.AsyncClient,
    *,
    goal: str = DEFAULT_GOAL,
    timeout_s: float = 1800.0,
    events: EventFeed | None = None,
) -> list[str]:
    """Les étapes réussies, dans l'ordre ; `CheckFailed` à la première ratée. `events` : lecture
    des événements d'une session (par défaut, le WebSocket de l'API de `client`)."""
    run = Run(client, events or websocket_feed(client), timeout_s)
    actions = {
        "santé": _health,
        "objectif": lambda r: _goal(r, goal),
        "cadrage": check_framing,
        "conseil": check_council,
        "choix": _choose,
        "programme": check_program,
        "validation": _validate,
        "leçons": check_lessons,
        "exports": _exports,
    }
    done: list[str] = []
    for step in STEPS:
        await actions[step](run)
        done.append(step)
        print(f"[ok] {step}", flush=True)
    return done


async def _main(api: str, timeout_s: float) -> int:
    base = api.rstrip("/")
    async with httpx.AsyncClient(base_url=base, timeout=HTTP_TIMEOUT_S) as client:
        try:
            steps = await run_check(client, timeout_s=timeout_s)
        except CheckFailed as failed:
            print(f"[échec] {failed.step} : {failed}", file=sys.stderr, flush=True)
            return 1
    print(f"Contrôle de fin de phase 4 réussi : {len(steps)} étapes sur {len(STEPS)}.")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Contrôle de fin de phase 4 (SPEC 18.1).")
    parser.add_argument("--api", default="http://localhost:8000", help=f"racine de l'API ({API})")
    parser.add_argument("--timeout", type=float, default=1800.0, help="délai total en secondes")
    args = parser.parse_args(argv)
    sys.exit(asyncio.run(_main(args.api, args.timeout)))


if __name__ == "__main__":
    main()
