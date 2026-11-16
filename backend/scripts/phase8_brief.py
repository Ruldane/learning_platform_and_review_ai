"""Partie `brief` du contrôle de la phase 8 : le brief du matin avec le modèle réel et la recherche
web. `GET /brief/today` le rend, et le crée s'il manque (origine `opening`) : cette partie se
lance donc quand le brief existe, ou n'importe quand (la partie `planifie` demande, elle, un jour
sans brief).

Étape `rubriques` : les sept rubriques sont là, leurs plafonds tenus. Étape `conseil` : prêt en 3
minutes au plus (`failed` et `unavailable` sont définitifs : dits tels quels), deux phrases,
chaque nombre cité figure dans les rubriques ; durée, appels du modèle et coût dits. Étape
`ressource` : un lien http(s) de son site, ou `null` (dit). Étape `relecture` : un second `GET`
rend le même brief (même `id`, même conseil, même ressource). Rien de ce qui est reçu n'apparaît
dans la sortie : seulement des étapes, des nombres, des codes et des identifiants."""

import time
from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_steps import within
from scripts.phase8_common import Track, cost_of, llm_calls, wait_for
from scripts.phase8_rules import check_advice, check_resource, check_rubrics

ADVICE_S = 180.0  # le conseil en 3 minutes au plus (la ressource, puis les deux phrases)


async def _today(run: Run, step: str) -> dict[str, Any]:
    found: dict[str, Any] = await expect_ok(run, step, "GET", "/brief/today")
    return found


async def check_sections(run: Run, st: Track) -> None:
    step = "rubriques"
    brief = await _today(run, step)
    check_rubrics(step, brief)
    st.brief = brief
    print(
        f"    brief {brief['id']} (origine {brief['origin']}) : {brief['reviews']['queue']} "
        f"fiche(s), {brief['reminders']['due']} relance(s) due(s), "
        f"{len(brief['offers']['items'])} offre(s), bloc "
        f"{'oui' if brief['block'] else 'non'}, semaine {'oui' if brief['week'] else 'non'}",
        flush=True,
    )


async def check_advice_step(run: Run, st: Track) -> None:
    step = "conseil"
    if not st.brief:
        raise CheckFailed(step, "Aucun brief lu : « rubriques » d'abord.")
    brief_id, began = st.brief["id"], time.monotonic()
    view: dict[str, Any] = {}

    async def settled() -> bool:
        view.update(await _today(run, step))
        if view["id"] != brief_id:
            raise CheckFailed(step, "Le brief du jour a changé d'identifiant pendant l'attente.")
        return bool(view["advice_status"] != "pending")

    await wait_for(within(run, ADVICE_S), step, settled, "conseil toujours en attente", ADVICE_S)
    seconds = time.monotonic() - began
    st.brief = dict(view)
    cited = check_advice(step, view)
    session_id = view["session_id"]
    spent = (
        f"{await llm_calls(run, session_id)} appel(s) LLM ; {await cost_of(run, step, session_id)}"
    )
    print(
        f"    conseil prêt en {seconds:.0f} s : 2 phrases, {cited} nombre(s) cité(s) ; {spent}",
        flush=True,
    )


async def check_resource_step(run: Run, st: Track) -> None:
    step = "ressource"
    domain = check_resource(step, st.brief["resource"])
    print(
        f"    ressource lue sur {domain}" if domain else "    aucune ressource (null)", flush=True
    )


async def check_reread(run: Run, st: Track) -> None:
    step = "relecture"
    again = await _today(run, step)
    first = st.brief
    if again["id"] != first["id"]:
        raise CheckFailed(step, f"Second GET : brief {again['id']}, {first['id']} attendu.")
    for key in ("advice", "resource", "advice_status", "origin"):
        if again[key] != first[key]:
            raise CheckFailed(step, f"Second GET : la rubrique « {key} » a changé.")
    print(f"    second GET : même brief {again['id']}", flush=True)
