"""Étape « une phrase » du contrôle de la phase 7 (`check_phase7`) : l'Assistant de suivi lit une
phrase de January (« j'ai postulé hier sur LinkedIn chez X pour le poste Y »), montre la fiche en
préparation (question `application_confirm`), puis la crée quand elle répond « Créer la fiche ».
Relançable : l'entreprise de la phrase change à chaque passage (la première d'une liste qu'aucune
fiche ne porte déjà), une session d'intake restée en attente est annulée. Rien de ce qui est
envoyé ou reçu n'apparaît dans un message d'échec ni dans la sortie : seulement des étapes, des
nombres, des codes et des identifiants."""

import time
from datetime import timedelta
from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok, wait_question
from scripts.phase6_rules import plain
from scripts.phase6_steps import cost_of, within
from scripts.phase7_common import (
    Track,
    expect_refusal,
    llm_calls,
    parse_day,
    send,
    today_of,
    wait_session,
)

INTAKE_S = 300.0  # la question de confirmation en 5 minutes au plus
SAVE_S = 60.0
KIND = "application_confirm"
PREFIX = "Maison Contrôle"
POSITION = "Ingénieure Données"
NAMES = (
    "Cèdre", "Dune", "Embrun", "Fougère", "Glycine", "Horizon", "Iris", "Jasmin", "Lagune",
    "Mistral", "Nacre", "Orchidée", "Prairie", "Quartz", "Rivage", "Sauge", "Tilleul", "Uranie",
    "Vigne", "Zéphyr",
)  # fmt: skip


def fresh_company(used: set[str]) -> str:
    """La première entreprise de la liste qu'aucune fiche ne porte encore."""
    for name in NAMES:
        company = f"{PREFIX} {name}"
        if plain(company) not in used:
            return company
    raise CheckFailed("une phrase", "Les entreprises du contrôle sont toutes déjà prises.")


def sentence_of(company: str) -> str:
    return f"j'ai postulé hier sur LinkedIn chez {company} pour le poste {POSITION}"


async def _cancel_previous(run: Run, step: str, session_id: str) -> None:
    """Annule la phrase restée en attente d'un passage précédent (rien n'est créé)."""
    question = await wait_question(within(run, INTAKE_S), step, session_id, KIND)
    body = {"interrupt_id": question["interrupt_id"], "value": {"choice": "cancel"}}
    await expect_ok(run, step, "POST", f"/sessions/{session_id}/resume", json=body)
    await wait_session(within(run, SAVE_S), step, session_id, "annulation jamais terminée")


async def _start(run: Run, step: str, text: str) -> str:
    for _ in range(2):
        response = await send(run, step, "POST", "/applications/intake", json={"text": text})
        if response.status_code == 202:
            return str(response.json()["session_id"])
        expect_refusal(response, step, "POST /applications/intake", 409, "intake_in_progress")
        await _cancel_previous(run, step, str(response.json()["error"]["details"]["session_id"]))
    raise CheckFailed(step, "Une phrase reste en cours malgré son annulation.")


def _fields(question: dict[str, Any]) -> dict[str, str]:
    return {item["id"]: item.get("value") or "" for item in question["fields"]}


def check_question(step: str, question: dict[str, Any], company: str, yesterday: str) -> None:
    """La fiche montrée : entreprise, poste, statut, jour et canal justes, rien d'inventé, aucune
    alerte (options « Créer » et « Annuler »)."""
    values = _fields(question)
    wrong = [
        name
        for name, ok in (
            ("company", plain(values["company"]) == plain(company)),
            ("title", plain(values["title"]) == plain(POSITION)),
            ("status", values["status"] == "applied"),
            ("applied_on", values["applied_on"] == yesterday),
            ("channel", values["channel"] == "linkedin"),
            ("contact_name", values["contact_name"] == ""),
            ("contact_role", values["contact_role"] == ""),
        )
        if not ok
    ]
    if wrong:
        raise CheckFailed(step, f"Champ(s) de la fiche montrée faux : {', '.join(wrong)}.")
    options = [option["value"] for option in question["options"]]
    if options != ["create", "cancel"] or question["question"] != "Create this application?":
        raise CheckFailed(step, f"Question ou options inattendues ({', '.join(options)}).")


async def _created_fiche(run: Run, step: str, session_id: str) -> str:
    events = await run.events(session_id)
    ready = [e["payload"] for e in events if e["type"] == "artifact.ready"]
    fiches = [p["artifact_id"] for p in ready if p.get("kind") == "application"]
    if len(fiches) != 1:
        raise CheckFailed(step, f"{len(fiches)} fiche(s) annoncée(s) par la session : 1 attendue.")
    return str(fiches[0])


async def check_intake(run: Run, st: Track) -> None:
    step = "une phrase"
    began = time.monotonic()
    yesterday = (await today_of(run, step) - timedelta(days=1)).isoformat()
    used = {plain(a["company"]) for a in await expect_ok(run, step, "GET", "/applications")}
    company = fresh_company(used)
    sid = await _start(run, step, sentence_of(company))
    busy = await send(run, step, "POST", "/applications/intake", json={"text": "autre phrase"})
    expect_refusal(busy, step, "Seconde phrase", 409, "intake_in_progress")
    if busy.json()["error"]["details"].get("session_id") != sid:
        raise CheckFailed(step, "Le 409 désigne une autre session que celle en cours.")
    question = await wait_question(within(run, INTAKE_S), step, sid, KIND)
    seconds = time.monotonic() - began
    check_question(step, question, company, yesterday)
    body = {"interrupt_id": question["interrupt_id"], "value": {"choice": "create"}}
    await expect_ok(run, step, "POST", f"/sessions/{sid}/resume", json=body)
    await wait_session(within(run, SAVE_S), step, sid, "création jamais terminée")
    st.intake_id = await _created_fiche(run, step, sid)
    detail = await expect_ok(run, step, "GET", f"/applications/{st.intake_id}")
    _check_created(step, detail, company, yesterday, sid)
    calls, cost = await llm_calls(run, sid), await cost_of(run, step, sid)
    print(
        f"    question en {seconds:.0f} s, fiche {st.intake_id} créée (postulée la veille, "
        f"canal LinkedIn), {calls} appel(s) LLM ; {cost}",
        flush=True,
    )


def _check_created(step: str, detail: dict[str, Any], company: str, day: str, sid: str) -> None:
    created = detail["events"][0] if detail["events"] else {}
    if (plain(detail["company"]), plain(detail["title"])) != (plain(company), plain(POSITION)):
        raise CheckFailed(step, f"Fiche {detail['id']} : entreprise ou poste différents.")
    if (detail["status"], detail["channel"]) != ("applied", "linkedin"):
        raise CheckFailed(step, f"Fiche {detail['id']} : statut ou canal faux.")
    if parse_day(detail["applied_on"]) != parse_day(day):
        raise CheckFailed(step, f"Fiche {detail['id']} : jour de candidature faux.")
    if created.get("kind") != "created" or created.get("ref_id") != sid:
        raise CheckFailed(step, f"Fiche {detail['id']} : née d'une autre session que la phrase.")
