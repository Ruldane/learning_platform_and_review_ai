"""Étape « kit » du contrôle de la phase 7 (`check_phase7`) : le kit de candidature de la fiche née
de l'offre fictive, avec le modèle réel : sept pièces en parallèle (dossier de l'entreprise avec
recherche web), la lettre de 250 à 350 mots dans la langue de l'offre, aucune réponse salariale
remplie, chaque pièce « à vérifier » avec ses termes (absents du profil), un dossier d'au moins
une source, puis l'archive `kit.zip`. Rien de ce qui est envoyé ou reçu n'apparaît dans un message
d'échec ni dans la sortie : seulement des étapes, des nombres, des codes et des noms de pièces ;
les termes signalés se lisent par l'API."""

import time
from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_steps import cost_of, within
from scripts.phase7_common import Track, code_of, count_calls, expect_refusal, send, wait_session
from scripts.phase7_fiche import load_prerequisites
from scripts.phase7_rules import (
    check_dossier,
    check_form,
    check_items,
    check_lengths,
    check_letter,
    check_to_check,
    check_zip,
    profile_text,
)

KIT_S = 900.0  # le kit en 15 minutes au plus (sept pièces, recherche web, modèle lent)
ZIP_NAME_PREFIX = "Kit_"


async def _start(run: Run, step: str, application_id: str) -> str:
    """Lance le kit ; un kit déjà ouvert (409) est repris par sa session. Un second lancement
    pendant le premier est refusé (409 `kit_in_progress`, la même session)."""
    path = f"/applications/{application_id}/kit"
    started = await send(run, step, "POST", path)
    if started.status_code == 202:
        session_id = str(started.json()["session_id"])
    else:
        expect_refusal(started, step, f"POST {path}", 409, "kit_in_progress")
        session_id = str(started.json()["error"]["details"]["session_id"])
        print(f"    kit {session_id} déjà ouvert : repris", flush=True)
    again = await send(run, step, "POST", path)
    expect_refusal(again, step, "Second lancement", 409, "kit_in_progress")
    if again.json()["error"]["details"].get("session_id") != session_id:
        raise CheckFailed(step, "Le 409 désigne une autre session que celle du kit.")
    return session_id


async def _read(run: Run, step: str, application_id: str, session_id: str) -> list[dict[str, Any]]:
    kit = await expect_ok(run, step, "GET", f"/applications/{application_id}/kit")
    if kit["running"] or kit["session_id"] != session_id:
        raise CheckFailed(
            step, f"Kit {session_id} terminé mais lu comme en cours ou autre session."
        )
    items: list[dict[str, Any]] = kit["items"]
    check_items(step, items)
    return items


def _check_pieces(step: str, items: list[dict[str, Any]], st: Track) -> dict[str, int]:
    """Les règles de chaque pièce ; rend les termes signalés par pièce « à vérifier »."""
    profile = profile_text(st.profile)
    language = str(st.posting["analysis"]["language"])
    letter = next(item for item in items if item["kind"] == "letter")
    form = next(item for item in items if item["kind"] == "form_answers")
    check_letter(step, letter, language)
    check_form(step, form)
    flagged: dict[str, int] = {}
    for item in items:
        check_lengths(step, item)
        if item["status"] == "to_check":
            flagged[item["kind"]] = check_to_check(step, item, profile)
    check_dossier(step, next(item for item in items if item["kind"] == "company_brief"))
    return flagged


async def _check_events(
    run: Run, step: str, application_id: str, feed: list[dict[str, Any]]
) -> None:
    detail = await expect_ok(run, step, "GET", f"/applications/{application_id}")
    kit_events = [e for e in detail["events"] if e["kind"] == "kit"]
    if len(kit_events) < 2 or not kit_events[-1]["text"].startswith("Kit de candidature terminé"):
        raise CheckFailed(step, f"Fil de la fiche : {len(kit_events)} événement(s) « kit ».")
    ready = [
        e for e in feed if e["type"] == "artifact.ready" and e["payload"]["kind"] == "kit_item"
    ]
    if len(ready) < 7:
        raise CheckFailed(step, f"{len(ready)} pièce(s) annoncée(s) en direct : 7 attendues.")


async def _download(run: Run, step: str, application_id: str, items: list[dict[str, Any]]) -> int:
    response = await send(run, step, "GET", f"/applications/{application_id}/kit.zip")
    disposition = response.headers.get("content-disposition", "")
    if response.status_code != 200 or response.headers.get("content-type") != "application/zip":
        raise CheckFailed(step, f"kit.zip : HTTP {response.status_code} ({code_of(response)}).")
    if (
        not disposition.startswith("attachment")
        or f'filename="{ZIP_NAME_PREFIX}' not in disposition
    ):
        raise CheckFailed(step, "kit.zip : en-tête de téléchargement inattendu.")
    return check_zip(step, response.content, items)


async def check_kit(run: Run, st: Track) -> None:
    step = "kit"
    if not st.application_id:
        raise CheckFailed(step, "Aucune fiche de l'offre : « fiche depuis offre » d'abord.")
    if not st.profile:
        await load_prerequisites(run, st, step)
    began = time.monotonic()
    session_id = await _start(run, step, st.application_id)
    await wait_session(within(run, KIT_S), step, session_id, "kit jamais terminé")
    seconds = time.monotonic() - began
    items = await _read(run, step, st.application_id, session_id)
    flagged = _check_pieces(step, items, st)
    feed = await run.events(session_id)
    await _check_events(run, step, st.application_id, feed)
    files = await _download(run, step, st.application_id, items)
    words = next(i["words"] for i in items if i["kind"] == "letter")
    statuses = {s: sum(1 for i in items if i["status"] == s) for s in ("ready", "to_check")}
    brief = next(i for i in items if i["kind"] == "company_brief")
    print(
        f"    kit {session_id} en {seconds:.0f} s : 7 pièces ({statuses['ready']} prêtes, "
        f"{statuses['to_check']} à vérifier), {count_calls(feed)} appel(s) LLM ; "
        f"{await cost_of(run, step, session_id)}",
        flush=True,
    )
    detail = ", ".join(f"{kind} {n} terme(s)" for kind, n in flagged.items()) or "aucune"
    print(
        f"    lettre de {words} mots ; à vérifier : {detail} ; dossier de "
        f"{len(brief['sources'])} source(s) ; kit.zip lisible ({files} fichiers)",
        flush=True,
    )
