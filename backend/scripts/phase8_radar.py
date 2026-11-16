"""Partie `radar` du contrôle de la phase 8 : un relevé du radar du marché avec le modèle réel, la
recherche web et la lecture des pages. Un poste et une zone fictifs, génériques (`ROLE`, `ZONE`).

Étape `lancement` : `POST /radar/runs` rend 202, un second `POST` pendant le relevé rend 409
`radar_in_progress` avec le même relevé ; le poste et la zone des réglages sont remis comme avant.
Étape `relevé` : fini (`done`) en 15 minutes au plus ; durée, appels du modèle et coût dits. Étape
`rapport` : lectures et plafonds, offres et classement, `low_sample`, et chaque salaire rapporté
présent dans la page relue de l'offre (une page injoignable est comptée, pas jugée). Rien de ce
qui est envoyé ou reçu n'apparaît dans la sortie : seulement des étapes, des nombres, des codes et
des identifiants."""

import time
from typing import Any

import httpx

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_steps import within
from scripts.phase7_common import code_of, details_of, expect_refusal, send
from scripts.phase8_common import Track, cost_of, llm_calls, settings_kept, wait_for
from scripts.phase8_rules import ROLE, ZONE, check_report, salary_missing

RADAR_S = 900.0  # le relevé en 15 minutes au plus (recherche, 60 lectures, extraction par lots)
PAGE_TIMEOUT_S = 30.0
SESSION = "session"


async def check_launch(run: Run, st: Track) -> None:
    step = "lancement"
    body = {"role": ROLE, "zone": ZONE}
    async with settings_kept(run, step):
        started = await send(run, step, "POST", "/radar/runs", json=body)
        if started.status_code != 202:
            raise CheckFailed(
                step, f"POST /radar/runs : HTTP {started.status_code} ({code_of(started)})."
            )
        st.radar = {"id": str(started.json()["run_id"]), SESSION: str(started.json()["session_id"])}
        again = await send(run, step, "POST", "/radar/runs", json=body)
        expect_refusal(again, step, "Second lancement", 409, "radar_in_progress")
        if details_of(again).get("run_id") != st.radar["id"]:
            raise CheckFailed(step, "Le 409 désigne un autre relevé que celui qui tourne.")
    print(f"    relevé {st.radar['id']} lancé (session {st.radar[SESSION]})", flush=True)


async def _read(run: Run, step: str, run_id: str) -> dict[str, Any]:
    found: dict[str, Any] = await expect_ok(run, step, "GET", f"/radar/runs/{run_id}")
    return found


async def check_run(run: Run, st: Track) -> None:
    step = "relevé"
    if not st.radar:
        raise CheckFailed(step, "Aucun relevé lancé : « lancement » d'abord.")
    run_id, session_id = st.radar["id"], st.radar[SESSION]
    began = time.monotonic()
    view: dict[str, Any] = {}

    async def finished() -> bool:
        view.update(await _read(run, step, run_id))
        if view["status"] == "failed":
            raise CheckFailed(
                step, f"Relevé {run_id} en échec ({view['error_code'] or 'sans code'})."
            )
        return bool(view["status"] == "done")

    await wait_for(within(run, RADAR_S), step, finished, "relevé jamais fini", RADAR_S)
    seconds = time.monotonic() - began
    st.radar = view | {SESSION: session_id}
    latest = await expect_ok(run, step, "GET", "/radar/latest")
    if (latest["latest"] or {}).get("id") != run_id or latest["running"] is not None:
        raise CheckFailed(
            step, "`/radar/latest` ne rend pas ce relevé fini, ou en rend un en cours."
        )
    print(
        f"    relevé {run_id} fini en {seconds:.0f} s, {await llm_calls(run, session_id)} appel(s) "
        f"LLM ; {await cost_of(run, step, session_id)}",
        flush=True,
    )


async def _salary_pages(run: Run, offers: list[dict[str, Any]]) -> tuple[int, int, int]:
    """`(rapportés, relus, injoignables)` : chaque salaire rapporté est cherché dans la page relue
    de son offre ; un nombre absent de la page est un échec."""
    step, reported, reread, unreachable = "rapport", 0, 0, 0
    for rank, offer in enumerate(offers, 1):
        if not offer["salary"]:
            continue
        reported += 1
        try:
            page = await run.client.get(
                str(offer["url"]), follow_redirects=True, timeout=PAGE_TIMEOUT_S
            )
            page.raise_for_status()
        except (httpx.HTTPError, httpx.InvalidURL):
            unreachable += 1
            continue
        reread += 1
        if salary_missing(str(offer["salary"]), page.text):
            raise CheckFailed(step, f"Salaire de l'offre n° {rank} absent de sa page relue.")
    return reported, reread, unreachable


async def check_report_step(run: Run, st: Track) -> None:
    step = "rapport"
    if not st.radar:
        raise CheckFailed(step, "Aucun relevé fini : « relevé » d'abord.")
    counts = check_report(step, st.radar)
    reported, reread, unreachable = await _salary_pages(run, st.radar["offers"])
    ranking = st.radar["ranking"]
    print(
        f"    {counts['read']} page(s) lue(s) dont {counts['not_postings']} sans offre, "
        f"{counts['blocked']} bloquée(s), {counts['analyzed']} offre(s) analysée(s) "
        f"({counts['not_analyzed']} lue(s) non analysée(s)), {counts['high']} à 70 ou plus ; "
        f"classement de {len(ranking)} compétence(s) ; échantillon "
        f"{'réduit' if st.radar['low_sample'] else 'suffisant'}",
        flush=True,
    )
    print(
        f"    salaires : {reported} rapporté(s), {reread} vérifié(s) dans la page, "
        f"{unreachable} page(s) injoignable(s)",
        flush=True,
    )
