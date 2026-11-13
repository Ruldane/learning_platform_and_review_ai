"""Contrôle de fin de phase 5, joué contre l'API en marche (Docker : le modèle réel ; tests :
modèles scriptés).

    uv run python -m scripts.check_phase5 --api http://localhost:8000 [--part etude] [--with-phase4]

Il faut un programme validé avec une leçon prête : celui de la phase 4, ou `--with-phase4` qui
lance d'abord `scripts.check_phase4` (programme et leçons réels). Partie `etude` : six étapes
(session guidée, quiz, fiches). Partie `tout` (par défaut) : douze, avec la carte de compétences
avant et après, la replanification de la semaine, la capture rapide, le bilan hebdomadaire et le
journal. Arrêt à la première ratée (`CheckFailed`, message en français, code de sortie 1). Rien
de ce qui est envoyé ou reçu n'est affiché : seulement les étapes, des nombres, des codes et des
identifiants. Le bilan hebdomadaire change l'heure du bilan dans les réglages (remise ensuite) et
attend la tâche planifiée jusqu'à 16 minutes ; le quiz n'atteint `valide` qu'au second passage
(nouvel essai à J+2, voir `phase5_quiz`)."""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Literal

import httpx

from scripts import check_phase4
from scripts.phase4_steps import API, CheckFailed, EventFeed, Run, expect_ok, websocket_feed
from scripts.phase5_capture import check_capture
from scripts.phase5_map import map_after, map_before
from scripts.phase5_quiz import play_quiz
from scripts.phase5_replan import replan_week
from scripts.phase5_steps import Etude, check_balance, check_cards, pick_program, play_session
from scripts.phase5_weekly import check_journal_step, weekly_review

type Part = Literal["etude", "tout"]

ETUDE_STEPS = ("santé", "programme", "session", "bilan de session", "quiz", "fiches")
ALL_STEPS = (
    "santé",
    "programme",
    "carte avant",
    "session",
    "bilan de session",
    "quiz",
    "fiches",
    "carte après",
    "replanification",
    "capture",
    "bilan hebdomadaire",
    "journal",
)
STEPS_BY_PART: dict[str, tuple[str, ...]] = {"etude": ETUDE_STEPS, "tout": ALL_STEPS}
REQUIRED_SERVICES = ("db", "llm")
HTTP_TIMEOUT_S = 60.0

__all__ = ["ALL_STEPS", "ETUDE_STEPS", "CheckFailed", "EventFeed", "main", "run_check"]


async def _health(run: Run, st: Etude) -> None:
    report = await expect_ok(run, "santé", "GET", "/health")
    checks: dict[str, Any] = report.get("checks", {})
    down = [name for name in REQUIRED_SERVICES if not checks.get(name, {}).get("ok")]
    if down:
        raise CheckFailed("santé", f"Service indisponible : {', '.join(down)}.")


async def run_check(
    client: httpx.AsyncClient,
    *,
    part: Part = "tout",
    with_phase4: bool = False,
    timeout_s: float = 3600.0,
    events: EventFeed | None = None,
) -> list[str]:
    """Les étapes réussies, dans l'ordre ; `CheckFailed` à la première ratée. `with_phase4` :
    `check_phase4.run_check` d'abord (programme et leçons réels). `events` : lecture des
    événements d'une session pour la phase 4 (par défaut, le WebSocket de l'API de `client`)."""
    feed = events or websocket_feed(client)
    if with_phase4:
        await check_phase4.run_check(client, timeout_s=timeout_s, events=feed)
    run = Run(client, feed, timeout_s)
    state = Etude()
    actions: dict[str, Callable[[Run, Etude], Awaitable[None]]] = {
        "santé": _health,
        "programme": pick_program,
        "carte avant": map_before,
        "session": play_session,
        "bilan de session": check_balance,
        "quiz": play_quiz,
        "fiches": check_cards,
        "carte après": map_after,
        "replanification": replan_week,
        "capture": check_capture,
        "bilan hebdomadaire": weekly_review,
        "journal": check_journal_step,
    }
    done: list[str] = []
    for step in STEPS_BY_PART[part]:
        await actions[step](run, state)
        done.append(step)
        print(f"[ok] {step}", flush=True)
    return done


async def _main(api: str, part: Part, with_phase4: bool, timeout_s: float) -> int:
    base = api.rstrip("/")
    async with httpx.AsyncClient(base_url=base, timeout=HTTP_TIMEOUT_S) as client:
        try:
            steps = await run_check(client, part=part, with_phase4=with_phase4, timeout_s=timeout_s)
        except CheckFailed as failed:
            print(f"[échec] {failed.step} : {failed}", file=sys.stderr, flush=True)
            return 1
    print(f"Contrôle de fin de phase 5 réussi : {len(steps)} étapes ({part}).")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Contrôle de fin de phase 5.")
    parser.add_argument("--api", default="http://localhost:8000", help=f"racine de l'API ({API})")
    parser.add_argument("--part", choices=("etude", "tout"), default="tout")
    parser.add_argument("--with-phase4", action="store_true", help="lance d'abord la phase 4")
    parser.add_argument("--timeout", type=float, default=3600.0, help="délai total en secondes")
    args = parser.parse_args(argv)
    sys.exit(asyncio.run(_main(args.api, args.part, args.with_phase4, args.timeout)))


if __name__ == "__main__":
    main()
