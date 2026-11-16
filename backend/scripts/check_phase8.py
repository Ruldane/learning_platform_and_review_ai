"""Contrôle de la phase 8 (quotidien), joué contre l'API en marche (Docker : GLM 5.3 flash réel,
SearXNG ; tests : fausse API). Même forme que `check_phase7` : relançable, une ligne par étape, code
de sortie 1 à la première ratée (`CheckFailed`, message en français).

Partie `planifie` (4 étapes, à lancer AVANT toute ouverture de l'accueil du jour) : `préalable`
(aucun brief du jour : sinon le script le dit et ne règle rien), `planification` (l'heure du brief
réglée 3 minutes plus tard, remise ensuite ; « Brief du jour prêt » relu au fil d'activité, qui ne
crée rien, 10 minutes au plus après l'heure), `origine` (le brief est d'origine `schedule`),
`journaux`. Partie `radar` (4 étapes) : `lancement` (poste et zone fictifs, second lancement :
409), `relevé` (fini en 15 minutes au plus ; durée, appels du modèle, coût), `rapport` (lectures,
plafonds, classement, `low_sample`, salaires relus dans les pages), `journaux`. Partie `brief` (5
étapes) : `rubriques`, `conseil` (prêt en 3 minutes au plus, deux phrases, nombres des rubriques),
`ressource`, `relecture` (même `id`), `journaux`.

Le script tourne hors du conteneur du back (les scripts n'y sont pas, `.dockerignore`) : dans un
conteneur jetable de la même image, sur le réseau de la pile, scripts montés ; les journaux du back
passent par l'entrée standard (`--logs-file -`), lus au lancement. Sans journaux, l'étape échoue.

    docker compose logs --no-color backend | docker run --rm -i \\
      --name learning_career_platform-check8 --network learning_career_platform_default \\
      --entrypoint python -v "$PWD/backend/scripts:/app/scripts:ro" \\
      learning_career_platform-backend:latest -m scripts.check_phase8 \\
      --api http://backend:8000 --part planifie --logs-file -

(`--part radar` pour le radar, `--part brief` pour le brief.) Les journaux sont lus au lancement :
un second passage couvre le premier. Rien de ce qui est envoyé ou reçu n'est affiché : seulement
des étapes, des nombres, des codes et des identifiants."""

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence
from typing import Literal

import httpx

from scripts.phase4_steps import API, CheckFailed, EventFeed, Run, websocket_feed
from scripts.phase8_brief import (
    check_advice_step,
    check_reread,
    check_resource_step,
    check_sections,
)
from scripts.phase8_common import Step, Track
from scripts.phase8_plan import check_origin, check_planned, check_prerequisite
from scripts.phase8_radar import check_launch, check_report_step, check_run
from scripts.phase8_rules import check_logs_8, log_extras

type Part = Literal["planifie", "radar", "brief"]

PLANIFIE_STEPS = ("préalable", "planification", "origine", "journaux")
RADAR_STEPS = ("lancement", "relevé", "rapport", "journaux")
BRIEF_STEPS = ("rubriques", "conseil", "ressource", "relecture", "journaux")
STEPS_BY_PART: dict[str, tuple[str, ...]] = {
    "planifie": PLANIFIE_STEPS,
    "radar": RADAR_STEPS,
    "brief": BRIEF_STEPS,
}
HTTP_TIMEOUT_S = 60.0
DEFAULT_TIMEOUT_S = 3600.0

__all__ = [
    "BRIEF_STEPS",
    "PLANIFIE_STEPS",
    "RADAR_STEPS",
    "STEPS_BY_PART",
    "CheckFailed",
    "main",
    "run_check",
]


def _logs_step(logs: str | None) -> Step:
    async def check(run: Run, st: Track) -> None:
        if logs is None:
            raise CheckFailed("journaux", "Journaux du back non fournis (--logs-file).")
        extra = log_extras(st.radar or None, st.brief or None)
        print(
            f"    {check_logs_8('journaux', logs, extra)} ligne(s) relue(s), sans donnée",
            flush=True,
        )

    return check


async def run_check(
    client: httpx.AsyncClient,
    *,
    part: Part = "planifie",
    timeout_s: float = DEFAULT_TIMEOUT_S,
    events: EventFeed | None = None,
    logs: str | None = None,
) -> list[str]:
    """Les étapes réussies, dans l'ordre ; `CheckFailed` à la première ratée. `logs` : les
    journaux du back à relire."""
    if part not in STEPS_BY_PART:
        raise CheckFailed("partie", f"Partie « {part} » inconnue.")
    run = Run(client, events or websocket_feed(client, part), timeout_s)
    state = Track()
    actions: dict[str, Step] = {
        "préalable": check_prerequisite,
        "planification": check_planned,
        "origine": check_origin,
        "lancement": check_launch,
        "relevé": check_run,
        "rapport": check_report_step,
        "rubriques": check_sections,
        "conseil": check_advice_step,
        "ressource": check_resource_step,
        "relecture": check_reread,
        "journaux": _logs_step(logs),
    }
    done: list[str] = []
    for step in STEPS_BY_PART[part]:
        began = time.monotonic()
        await actions[step](run, state)
        done.append(step)
        print(f"[ok] {step} ({time.monotonic() - began:.0f} s)", flush=True)
    return done


def _read_logs(path: str | None) -> str | None:
    if path is None:
        return None
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


async def _main(api: str, part: Part, timeout_s: float, logs: str | None) -> int:
    async with httpx.AsyncClient(base_url=api.rstrip("/"), timeout=HTTP_TIMEOUT_S) as client:
        try:
            steps = await run_check(client, part=part, timeout_s=timeout_s, logs=logs)
        except CheckFailed as failed:
            print(f"[échec] {failed.step} : {failed}", file=sys.stderr, flush=True)
            return 1
    print(f"Contrôle de la phase 8 réussi : {len(steps)} étapes ({part}).")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Contrôle de la phase 8 (quotidien).")
    parser.add_argument("--api", default="http://localhost:8000", help=f"racine de l'API ({API})")
    parser.add_argument("--part", choices=tuple(STEPS_BY_PART), default="planifie")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="délai total en secondes"
    )
    parser.add_argument("--logs-file", help="journaux du back (« - » : entrée standard)")
    args = parser.parse_args(argv)
    logs = _read_logs(args.logs_file)
    sys.exit(asyncio.run(_main(args.api, args.part, args.timeout, logs)))


if __name__ == "__main__":
    main()
