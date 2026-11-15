"""Étapes « relance » et « indicateurs » du contrôle de la phase 7 (`check_phase7`). Une fiche
postulée il y a 8 jours (avec un contact LinkedIn) doit porter la relance `linkedin_7` due, avec
son brouillon ; « Reporter » la repousse de 3 jours, « Fait » la clôt et passe la fiche à
« Relancée ». Les indicateurs sont recoupés avec la liste des fiches et celle des relances.
Relançable : la fiche de la relance change à chaque passage. Rien de ce qui est envoyé ou reçu
n'apparaît dans un message d'échec ni dans la sortie : seulement des étapes, des nombres, des codes
et des identifiants."""

from datetime import date, timedelta
from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_rules import plain
from scripts.phase7_common import Track, expect_refusal, parse_day, send, today_of

COMPANY_PREFIX = "Atelier Relance"
POSITION = "Ingénieure Logiciel"
CONTACT = {
    "name": "Alex Contrôle",
    "role": "Recruteur",
    "url": "https://www.linkedin.com/in/alex-controle-fictif",
}
SEARCH_PREFIX = "https://www.linkedin.com/search/results/people/?keywords="
STATUSES = (
    "to_apply", "applied", "followed_up", "interview", "offer", "rejected", "no_answer",
    "withdrawn",
)  # fmt: skip
WAITING_KINDS = ("linkedin_7", "email_14", "close_21")


async def _all_reminders(run: Run, step: str, app_id: str) -> dict[str, dict[str, Any]]:
    """Les relances d'une fiche, par sorte (toutes : dues, à venir, faites, ignorées)."""
    listed = await expect_ok(run, step, "GET", "/reminders", params={"due": "false"})
    return {r["kind"]: r for r in listed if r["application_id"] == app_id}


async def _create_waiting(run: Run, step: str, applied: date) -> tuple[str, str]:
    used = {plain(a["company"]) for a in await expect_ok(run, step, "GET", "/applications")}
    number = 1
    while plain(f"{COMPANY_PREFIX} {number}") in used:
        number += 1
    company = f"{COMPANY_PREFIX} {number}"
    body = {
        "company": company,
        "title": POSITION,
        "status": "applied",
        "applied_on": applied.isoformat(),
        "channel": "linkedin",
        "contacts": [CONTACT],
    }
    created = await send(run, step, "POST", "/applications", json=body)
    if created.status_code != 201:
        raise CheckFailed(step, f"POST /applications : HTTP {created.status_code}.")
    return str(created.json()["application"]["id"]), company


def _check_draft(step: str, reminder: dict[str, Any], company: str) -> int:
    draft = reminder["draft"]
    contact = reminder["contact"] or {}
    first_name = CONTACT["name"].split()[0]
    if len(draft) < 40 or company not in draft or POSITION not in draft or first_name not in draft:
        raise CheckFailed(step, "Brouillon de relance : entreprise, poste ou prénom absents.")
    if contact.get("name") != CONTACT["name"] or reminder["channel"] != "linkedin":
        raise CheckFailed(step, "Relance : contact ou canal LinkedIn faux.")
    if reminder["linkedin_search_url"] is not None:
        raise CheckFailed(step, "Relance avec contact : recherche LinkedIn proposée à tort.")
    return len(draft.split())


async def _check_without_contact(run: Run, step: str, intake_id: str) -> None:
    """La fiche de la phrase n'a pas de contact : la recherche LinkedIn est pré remplie."""
    reminders = await _all_reminders(run, step, intake_id)
    first = reminders.get("linkedin_7")
    if first is None:
        raise CheckFailed(step, f"Fiche {intake_id} postulée : relance linkedin_7 absente.")
    if first["contact"] is not None or first["channel"] != "linkedin":
        raise CheckFailed(step, f"Relance {first['id']} : contact ou canal faux.")
    if not str(first["linkedin_search_url"]).startswith(SEARCH_PREFIX) or not first["draft"]:
        raise CheckFailed(step, f"Relance {first['id']} : recherche LinkedIn ou brouillon absent.")


async def _act(run: Run, step: str, reminder_id: str, action: str) -> dict[str, Any]:
    response = await send(run, step, "PATCH", f"/reminders/{reminder_id}", json={"action": action})
    if response.status_code != 200:
        raise CheckFailed(step, f"PATCH /reminders : HTTP {response.status_code} ({action}).")
    return dict(response.json())


async def check_reminders(run: Run, st: Track) -> None:
    step = "relance"
    today = await today_of(run, step)
    settings = await expect_ok(run, step, "GET", "/settings")
    delays = [int(d) for d in settings.get("reminder_delays_days") or (7, 14, 21)]
    applied = today - timedelta(days=delays[0] + 1)
    st.reminder_app_id, company = await _create_waiting(run, step, applied)
    due = await expect_ok(run, step, "GET", "/reminders")
    mine = [r for r in due if r["application_id"] == st.reminder_app_id]
    if [r["kind"] for r in mine] != ["linkedin_7"] or mine[0]["status"] != "pending":
        raise CheckFailed(step, f"{len(mine)} relance(s) due(s) : linkedin_7 seule attendue.")
    words = _check_draft(step, mine[0], company)
    every = await _all_reminders(run, step, st.reminder_app_id)
    expected = {k: applied + timedelta(days=d) for k, d in zip(WAITING_KINDS, delays, strict=True)}
    if {k: parse_day(r["due_on"]) for k, r in every.items()} != expected:
        raise CheckFailed(step, "Échéances des relances différentes de celles des réglages.")
    if st.intake_id:
        await _check_without_contact(run, step, st.intake_id)
    reminder_id = mine[0]["id"]
    await _postpone_then_done(run, step, st.reminder_app_id, reminder_id, today)
    print(
        f"    fiche postulée il y a {delays[0] + 1} jours : relance linkedin_7 due avec brouillon "
        f"({words} mots), reportée au {today + timedelta(days=3)}, faite : fiche Relancée",
        flush=True,
    )


async def _postpone_then_done(
    run: Run, step: str, app_id: str, reminder_id: str, today: date
) -> None:
    bad = await send(run, step, "PATCH", f"/reminders/{reminder_id}", json={"action": "explode"})
    if bad.status_code != 422 or "explode" in bad.text:
        raise CheckFailed(step, f"Action inconnue : HTTP {bad.status_code}, 422 sans écho attendu.")
    postponed = await _act(run, step, reminder_id, "postpone")
    if postponed["status"] != "pending" or parse_day(postponed["due_on"]) != today + timedelta(3):
        raise CheckFailed(step, f"Relance {reminder_id} : report de 3 jours faux.")
    still_due = [r["id"] for r in await expect_ok(run, step, "GET", "/reminders")]
    if reminder_id in still_due:
        raise CheckFailed(step, f"Relance {reminder_id} reportée mais encore due.")
    done = await _act(run, step, reminder_id, "done")
    detail = await expect_ok(run, step, "GET", f"/applications/{app_id}")
    kinds = [e["kind"] for e in detail["events"]]
    if done["status"] != "done" or detail["status"] != "followed_up":
        raise CheckFailed(step, f"Relance {reminder_id} faite : fiche pas « Relancée ».")
    if "reminder" not in kinds or kinds.count("status") < 1:
        raise CheckFailed(step, f"Fiche {app_id} : relance ou statut absents du fil.")
    again = await send(run, step, "PATCH", f"/reminders/{reminder_id}", json={"action": "done"})
    expect_refusal(again, step, "Seconde action", 409, "reminder_closed")
    rest = await _all_reminders(run, step, app_id)
    if rest["email_14"]["status"] != "pending":
        raise CheckFailed(step, "La relance de 14 jours devait rester en attente.")


async def check_stats(run: Run, st: Track) -> None:
    step = "indicateurs"
    stats = await expect_ok(run, step, "GET", "/applications/stats")
    fiches = await expect_ok(run, step, "GET", "/applications")
    counts = {s: sum(1 for a in fiches if a["status"] == s) for s in STATUSES}
    if stats["by_status"] != counts:
        raise CheckFailed(step, "Fiches par statut différentes de la liste des fiches.")
    due = await expect_ok(run, step, "GET", "/reminders")
    if stats["due_reminders"] != len(due):
        raise CheckFailed(step, f"{stats['due_reminders']} relance(s) due(s) contre {len(due)}.")
    rate, mean = stats["response_rate"], stats["mean_response_days"]
    if (rate is not None and not 0 <= rate <= 1) or (mean is not None and mean < 0):
        raise CheckFailed(step, "Taux ou délai moyen de réponse hors bornes.")
    wanted = {"followed_up": st.reminder_app_id, "applied": st.intake_id}
    for status, app_id in wanted.items():
        if app_id and app_id not in [a["id"] for a in fiches if a["status"] == status]:
            raise CheckFailed(step, f"Fiche {app_id} absente du statut {status}.")
    print(
        f"    {len(fiches)} fiche(s) ({', '.join(f'{s} {n}' for s, n in counts.items() if n)}), "
        f"taux de réponse {rate}, délai moyen {mean}, {len(due)} relance(s) due(s)",
        flush=True,
    )
