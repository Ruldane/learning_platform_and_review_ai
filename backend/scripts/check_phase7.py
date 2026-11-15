"""Contrôle de la phase 7 (candidatures), joué contre l'API en marche (Docker : GLM 5.3 flash réel ;
tests : modèles scriptés). Même forme que `check_phase6` : relançable, une ligne par étape, code de
sortie 1 à la première ratée (`CheckFailed`, message en français).

Partie `suivi` (6 étapes) : `fiche depuis offre` (la fiche de l'offre fictive de la phase 6 est
créée par son `posting_id`, ou relue, avec sa version de CV prête), `doublon` (même lien : 409
certain ; intitulé « (H/F) » : 409 probable avec la date ; autre poste de la même entreprise :
information), `une phrase` (l'Assistant de suivi lit une phrase réelle, montre la fiche, la crée),
`relance` (fiche postulée il y a 8 jours : relance `linkedin_7` avec son brouillon, « Reporter »,
« Fait » : fiche « Relancée »), `indicateurs`, `journaux`. Partie `kit` (3 étapes) : la fiche de
l'offre relue, `kit` (sept pièces en parallèle, lettre de 250 à 350 mots dans la langue de l'offre,
aucune réponse salariale remplie, pièces « à vérifier » nommées avec des termes absents du profil,
dossier avec au moins une source, `kit.zip` lisible ; durée, appels LLM et nombre de pièces à
vérifier sont affichés), `journaux`. Les préalables (profil validé, offre fictive analysée, version
de CV prête) viennent du contrôle de la phase 6 (`check_phase6 --part tout`) : un manque est dit,
rien n'est refait.

Le script tourne hors du conteneur du back (les scripts n'y sont pas, `.dockerignore`) : dans un
conteneur jetable de la même image, sur le réseau de la pile, scripts montés ; les journaux du back
passent par l'entrée standard (`--logs-file -`), lus au lancement (un second passage couvre le
premier). Sans journaux, l'étape échoue.

    docker compose logs --no-color backend | docker run --rm -i \\
      --name learning_career_platform-check7 --network learning_career_platform_default \\
      --entrypoint python -v "$PWD/backend/scripts:/app/scripts:ro" \\
      learning_career_platform-backend:latest -m scripts.check_phase7 \\
      --api http://backend:8000 --part suivi --logs-file -

(`--part kit` pour le kit.) Rien de ce qui est envoyé ou reçu n'est affiché : seulement des étapes,
des nombres, des codes et des identifiants."""

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence
from typing import Literal

import httpx

from scripts.phase4_steps import API, CheckFailed, EventFeed, Run, websocket_feed
from scripts.phase7_common import Step, Track
from scripts.phase7_fiche import check_duplicates, check_from_posting
from scripts.phase7_intake import PREFIX, check_intake
from scripts.phase7_kit import check_kit
from scripts.phase7_remind import check_reminders, check_stats
from scripts.phase7_rules import check_logs

type Part = Literal["suivi", "kit"]

SUIVI_STEPS = (
    "fiche depuis offre",
    "doublon",
    "une phrase",
    "relance",
    "indicateurs",
    "journaux",
)
KIT_STEPS = ("fiche depuis offre", "kit", "journaux")
STEPS_BY_PART: dict[str, tuple[str, ...]] = {"suivi": SUIVI_STEPS, "kit": KIT_STEPS}
HTTP_TIMEOUT_S = 60.0
DEFAULT_TIMEOUT_S = 3600.0

__all__ = ["KIT_STEPS", "STEPS_BY_PART", "SUIVI_STEPS", "CheckFailed", "main", "run_check"]


def _logs_step(logs: str | None) -> Step:
    async def check(run: Run, st: Track) -> None:
        if logs is None:
            raise CheckFailed("journaux", "Journaux du back non fournis (--logs-file).")
        print(
            f"    {check_logs('journaux', logs, (PREFIX,))} ligne(s) relue(s), sans donnée",
            flush=True,
        )

    return check


async def run_check(
    client: httpx.AsyncClient,
    *,
    part: Part = "suivi",
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
        "fiche depuis offre": check_from_posting,
        "doublon": check_duplicates,
        "une phrase": check_intake,
        "relance": check_reminders,
        "indicateurs": check_stats,
        "kit": check_kit,
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
    print(f"Contrôle de la phase 7 réussi : {len(steps)} étapes ({part}).")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Contrôle de la phase 7 (candidatures).")
    parser.add_argument("--api", default="http://localhost:8000", help=f"racine de l'API ({API})")
    parser.add_argument("--part", choices=("suivi", "kit"), default="suivi")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="délai total en secondes"
    )
    parser.add_argument("--logs-file", help="journaux du back (« - » : entrée standard)")
    args = parser.parse_args(argv)
    logs = _read_logs(args.logs_file)
    sys.exit(asyncio.run(_main(args.api, args.part, args.timeout, logs)))


if __name__ == "__main__":
    main()
