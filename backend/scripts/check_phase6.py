"""Contrôle de la phase 6 (CV), joué contre l'API en marche (Docker : GLM 5.3 flash réel ; tests :
modèles scriptés). Même forme que `check_phase5` (D116) : relançable, une ligne par étape, code de
sortie 1 à la première ratée (`CheckFailed`, message en français).

    docker compose logs --no-color backend \\
      | docker compose exec -T backend python -m scripts.check_phase6 --part capture --logs-file -

Partie `capture` (6.11) : profil maître importé puis validé, modèle de CV capturé puis validé,
offre par texte, lien illisible, écart, journaux. Les parties `revue` et `tout` viennent en 6.20.
Les journaux du back sont lus dans `--logs-file` (`-` : l'entrée standard), car le conteneur n'a
pas la CLI `docker` (preflight G23) : ils sont lus au lancement, donc la vérification couvre les
passages précédents (relancer une fois après un passage qui a tout fait : rien n'est refait).
Sans journaux, l'étape échoue. Rien de ce qui est envoyé ou reçu n'est affiché : seulement des
étapes, des nombres, des codes et des identifiants."""

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence
from typing import Literal

import httpx

from scripts.phase4_steps import API, CheckFailed, EventFeed, Run, websocket_feed
from scripts.phase6_postings import check_gap, check_posting, check_unreadable
from scripts.phase6_rules import check_logs
from scripts.phase6_steps import Capture, Step, check_design, check_profile

type Part = Literal["capture", "revue", "tout"]

CAPTURE_STEPS = ("profil", "design", "offre par texte", "lien illisible", "écart", "journaux")
STEPS_BY_PART: dict[str, tuple[str, ...]] = {"capture": CAPTURE_STEPS}
HTTP_TIMEOUT_S = 60.0

__all__ = ["CAPTURE_STEPS", "CheckFailed", "main", "run_check"]


def _logs_step(logs: str | None) -> Step:
    async def check(run: Run, st: Capture) -> None:
        if logs is None:
            raise CheckFailed("journaux", "Journaux du back non fournis (--logs-file).")
        print(f"    {check_logs('journaux', logs)} ligne(s) relue(s), sans donnée", flush=True)

    return check


async def run_check(
    client: httpx.AsyncClient,
    *,
    part: Part = "capture",
    fresh: bool = False,
    timeout_s: float = 1800.0,
    events: EventFeed | None = None,
    logs: str | None = None,
) -> list[str]:
    """Les étapes réussies, dans l'ordre ; `CheckFailed` à la première ratée. `fresh` : refait le
    profil et le modèle même s'ils existent ; `logs` : les journaux du back à relire."""
    if part not in STEPS_BY_PART:
        raise CheckFailed("partie", f"Partie « {part} » pas encore écrite (tâche 6.20).")
    run = Run(client, events or websocket_feed(client, "capture"), timeout_s)
    state = Capture(fresh=fresh)
    actions: dict[str, Step] = {
        "profil": check_profile,
        "design": check_design,
        "offre par texte": check_posting,
        "lien illisible": check_unreadable,
        "écart": check_gap,
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


async def _main(api: str, part: Part, fresh: bool, timeout_s: float, logs: str | None) -> int:
    async with httpx.AsyncClient(base_url=api.rstrip("/"), timeout=HTTP_TIMEOUT_S) as client:
        try:
            steps = await run_check(client, part=part, fresh=fresh, timeout_s=timeout_s, logs=logs)
        except CheckFailed as failed:
            print(f"[échec] {failed.step} : {failed}", file=sys.stderr, flush=True)
            return 1
    print(f"Contrôle de la phase 6 réussi : {len(steps)} étapes ({part}).")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Contrôle de la phase 6 (CV).")
    parser.add_argument("--api", default="http://localhost:8000", help=f"racine de l'API ({API})")
    parser.add_argument("--part", choices=("capture", "revue", "tout"), default="capture")
    parser.add_argument("--fresh", action="store_true", help="refait le profil et le modèle")
    parser.add_argument("--timeout", type=float, default=1800.0, help="délai total en secondes")
    parser.add_argument("--logs-file", help="journaux du back (« - » : entrée standard)")
    args = parser.parse_args(argv)
    logs = _read_logs(args.logs_file)
    sys.exit(asyncio.run(_main(args.api, args.part, args.fresh, args.timeout, logs)))


if __name__ == "__main__":
    main()
