"""Étapes « fiche depuis offre » et « doublon » du contrôle de la phase 7 (`check_phase7`). Les
préalables viennent de la phase 6 de la pile : le profil maître validé, l'offre fictive analysée et
une version de CV prête (aucune revue n'est refaite ici : un manque est dit en français). La fiche
née de l'offre est créée par son `posting_id` (ou relue si elle existe : relançable) ; une seconde
création de la même offre est refusée (409). Les doublons sont ceux de la SPEC 6.3 : même lien
(certain), même entreprise et intitulé « (H/F) » (probable), autre poste de la même entreprise
(information). Rien de ce qui est envoyé ou reçu n'apparaît dans un message d'échec ni dans la
sortie : seulement des étapes, des nombres, des codes et des identifiants."""

from typing import Any

import httpx

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_postings import TITLE
from scripts.phase7_common import (
    COMPANY,
    MANUAL_TITLE,
    MANUAL_URL,
    Track,
    code_of,
    details_of,
    expect_refusal,
    parse_day,
    send,
)

PHASE6 = "Lancer d'abord le contrôle de la phase 6 (--part tout)."


async def _ready_version(run: Run, step: str, posting_id: str) -> dict[str, Any] | None:
    versions = await expect_ok(run, step, "GET", f"/cv/versions?posting_id={posting_id}")
    ready: list[dict[str, Any]] = [v for v in versions if v["status"] == "ready"]
    return ready[0] if ready else None  # la plus récente d'abord


async def load_prerequisites(run: Run, st: Track, step: str) -> None:
    """Profil validé, offre fictive prête et version de CV prête : relus, jamais refaits."""
    state = await expect_ok(run, step, "GET", "/profile")
    if not state.get("validated"):
        raise CheckFailed(step, f"Aucun profil maître validé. {PHASE6}")
    st.profile = state["validated"]["data"]
    listed = await expect_ok(run, step, "GET", "/postings")
    candidates = [
        p
        for p in listed
        if p["status"] == "ready" and TITLE.casefold() in (p["title"] or "").casefold()
    ]
    for summary in candidates:
        version = await _ready_version(run, step, summary["id"])
        if version is not None:
            st.posting = await expect_ok(run, step, "GET", f"/postings/{summary['id']}")
            st.version = version
            return
    if not candidates:
        raise CheckFailed(step, f"Aucune offre fictive analysée. {PHASE6}")
    raise CheckFailed(step, f"Aucune version de CV prête pour l'offre fictive. {PHASE6}")


def _check_fiche(step: str, detail: dict[str, Any], st: Track) -> None:
    posting, analysis = st.posting, st.posting["analysis"]
    if detail["posting_id"] != posting["id"] or detail["posting_text"] != posting["text"]:
        raise CheckFailed(
            step, f"Fiche {detail['id']} : offre ou texte figé différents de l'offre."
        )
    wanted = (posting["company"] or analysis["company"], posting["title"] or analysis["title"])
    if (detail["company"], detail["title"]) != wanted:
        raise CheckFailed(step, f"Fiche {detail['id']} : entreprise ou intitulé différents.")
    followed = (detail["cv_version_id"], detail["cv_version_number"])
    if detail["cv_version_id"] is None or (
        detail["status"] == "to_apply" and followed != (st.version["id"], st.version["number"])
    ):
        raise CheckFailed(step, f"Fiche {detail['id']} : version de CV prête non reliée.")
    if not detail["events"] or detail["events"][0]["kind"] != "created":
        raise CheckFailed(step, f"Fiche {detail['id']} : événement « created » absent du fil.")


async def check_from_posting(run: Run, st: Track) -> None:
    step = "fiche depuis offre"
    await load_prerequisites(run, st, step)
    posting_id = st.posting["id"]
    first = await send(run, step, "POST", "/applications", json={"posting_id": posting_id})
    if first.status_code == 201:
        st.application_id = str(first.json()["application"]["id"])
        how = "créée par son offre (201)"
    else:
        expect_refusal(first, step, "POST /applications", 409, "application_exists")
        st.application_id = str(details_of(first)["application_id"])
        how = "déjà là (409 application_exists) : relue"
    again = await send(run, step, "POST", "/applications", json={"posting_id": posting_id})
    expect_refusal(again, step, "Seconde création", 409, "application_exists")
    if details_of(again).get("application_id") != st.application_id:
        raise CheckFailed(step, "Le 409 désigne une autre fiche que celle de l'offre.")
    listed = await expect_ok(run, step, "GET", f"/applications?posting_id={posting_id}")
    if [a["id"] for a in listed] != [st.application_id]:
        raise CheckFailed(step, f"{len(listed)} fiche(s) pour l'offre : une seule attendue.")
    detail = await expect_ok(run, step, "GET", f"/applications/{st.application_id}")
    _check_fiche(step, detail, st)
    check = await expect_ok(run, step, "GET", f"/applications/check?posting_id={posting_id}")
    if (check["own"] or {}).get("id") != st.application_id or check["alerts"]:
        raise CheckFailed(step, "Le contrôle de l'offre ne rend pas sa fiche, ou une alerte.")
    print(
        f"    fiche {st.application_id} {how}, version n° {st.version['number']} reliée, "
        f"statut {detail['status']}, {len(detail['events'])} événement(s), "
        f"{len(detail['reminders'])} relance(s)",
        flush=True,
    )


async def _manual_fiche(run: Run, step: str, st: Track) -> str:
    """La fiche manuelle « Société Fictive / Développeuse IA (H/F) » : relue ou créée (201, et
    la fiche de l'offre, même entreprise, est alors signalée en information)."""
    listed = await expect_ok(run, step, "GET", "/applications")
    found = [a for a in listed if a["company"] == COMPANY and a["title"] == MANUAL_TITLE]
    if found:
        return str(found[0]["id"])
    body = {"company": COMPANY, "title": MANUAL_TITLE, "url": MANUAL_URL}
    created = await send(run, step, "POST", "/applications", json=body)
    if created.status_code != 201:
        code = code_of(created)
        raise CheckFailed(step, f"POST /applications : HTTP {created.status_code} ({code}).")
    info = created.json()["info"]
    if st.application_id not in [a["application_id"] for a in info]:
        raise CheckFailed(step, "La création ne signale pas l'autre fiche de l'entreprise.")
    return str(created.json()["application"]["id"])


def _alert_of(
    response: httpx.Response, step: str, label: str, level: str, wanted: str
) -> dict[str, Any]:
    expect_refusal(response, step, label, 409, "application_duplicate")
    alerts: list[dict[str, Any]] = details_of(response).get("alerts", [])
    hit = next((a for a in alerts if a["application_id"] == wanted), None)
    if hit is None or hit["level"] != level:
        raise CheckFailed(step, f"{label} : alerte « {level} » sur la fiche manuelle absente.")
    return hit


async def check_duplicates(run: Run, st: Track) -> None:
    step = "doublon"
    if not st.application_id:
        await check_from_posting(run, st)
    st.manual_id = await _manual_fiche(run, step, st)
    same_link = {"company": COMPANY, "title": "Autre intitulé", "url": MANUAL_URL}
    certain = await send(run, step, "POST", "/applications", json=same_link)
    _alert_of(certain, step, "Même lien", "certain", st.manual_id)
    by_url = await expect_ok(run, step, "GET", "/applications/check", params={"url": MANUAL_URL})
    levels = {a["application_id"]: a["level"] for a in by_url["alerts"]}
    if levels.get(st.manual_id) != "certain":
        raise CheckFailed(step, "Le contrôle par lien ne signale pas la fiche (certain).")
    probable = await send(
        run, step, "POST", "/applications", json={"company": COMPANY, "title": "Développeuse IA"}
    )
    alert = _alert_of(probable, step, "Intitulé « (H/F) »", "probable", st.manual_id)
    day = parse_day(alert["created_on"])
    if day is None or str(day.day) not in alert["message"] or "statut" not in alert["message"]:
        raise CheckFailed(step, "L'alerte probable ne dit pas la date de la fiche ni son statut.")
    check = await expect_ok(run, step, "GET", f"/applications/check?posting_id={st.posting['id']}")
    if st.manual_id not in [a["application_id"] for a in check["info"] if a["level"] == "info"]:
        raise CheckFailed(step, "Autre poste de la même entreprise : information absente.")
    if st.manual_id in [a["application_id"] for a in check["alerts"]]:
        raise CheckFailed(step, "Autre poste de la même entreprise : alerte au lieu d'information.")
    print(
        f"    fiche manuelle {st.manual_id} : même lien 409 certain, intitulé « (H/F) » 409 "
        f"probable (créée le {day}), autre poste de l'offre : information",
        flush=True,
    )
