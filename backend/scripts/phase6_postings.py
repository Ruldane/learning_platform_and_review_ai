"""Étapes « offre », « lien illisible » et « écart » du contrôle de la phase 6 (`check_phase6`) :
l'offre fictive collée puis analysée (titre, mots clés tirés du texte, même texte rendu une
seconde fois sans doublon), un lien illisible refusé sans écho, puis l'écart entre le profil validé
et l'offre. Relançable : l'offre déjà ajoutée est rendue telle quelle (200). Rien de ce qui est
envoyé ou reçu n'apparaît dans un message d'échec ni dans la sortie."""

import time
from typing import Any

import httpx

from scripts.phase4_steps import API, CheckFailed, Run, expect_ok
from scripts.phase6_rules import keywords_in_text
from scripts.phase6_steps import Capture, cost_of, within
from scripts.sample_posting import POSTING_TEXT

POSTING_S = 180.0  # analyse de l'offre en 3 minutes au plus
TITLE = "AI Product Engineer"
UNREADABLE_URL = "https://example.invalid/"


async def _post(run: Run, step: str, body: dict[str, str]) -> httpx.Response:
    try:
        return await run.client.post(f"{API}/postings", json=body)
    except httpx.HTTPError as exc:
        raise CheckFailed(step, f"API injoignable ({type(exc).__name__}).") from None


async def _analysed(run: Run, step: str, posting_id: str) -> dict[str, Any]:
    found: dict[str, Any] = {}

    async def ready() -> bool:
        found.update(await expect_ok(run, step, "GET", f"/postings/{posting_id}"))
        if found["status"] in ("rejected", "failed"):
            raise CheckFailed(step, f"Offre {posting_id} {found['status']}.")
        return bool(found["status"] == "ready")

    await within(run, POSTING_S).until(step, ready, "analyse de l'offre jamais prête")
    return found


async def check_posting(run: Run, st: Capture) -> None:
    step = "offre par texte"
    began = time.monotonic()
    first = await _post(run, step, {"text": POSTING_TEXT})
    if first.status_code not in (200, 201):
        raise CheckFailed(step, f"POST /postings : HTTP {first.status_code}.")
    st.posting_id = first.json()["posting"]["id"]
    posting = await _analysed(run, step, st.posting_id)
    seconds = time.monotonic() - began
    title = posting["analysis"]["title"]
    if TITLE.casefold() not in title.casefold():
        raise CheckFailed(step, f"Titre de l'offre {st.posting_id} différent de l'attendu.")
    kept = keywords_in_text(step, posting["analysis"])
    again = await _post(run, step, {"text": POSTING_TEXT})
    if again.status_code != 200 or again.json()["created"] is not False:
        raise CheckFailed(step, f"Second envoi : HTTP {again.status_code}, doublon créé.")
    sid = posting.get("gap_session_id") or first.json().get("session_id")
    cost = await cost_of(run, step, sid) if sid else "coût inconnu"
    print(
        f"    analyse prête en {seconds:.0f} s (HTTP {first.status_code}) : titre "
        f"{'exact' if title == TITLE else 'proche'}, {kept} mot(s) clé(s) gardé(s), "
        f"second envoi 200 ; {cost}",
        flush=True,
    )


async def check_unreadable(run: Run, st: Capture) -> None:
    step = "lien illisible"
    began = time.monotonic()
    response = await _post(run, step, {"url": UNREADABLE_URL})
    code = (response.json().get("error") or {}).get("code") if response.is_error else None
    if response.status_code != 422 or code != "posting_unreadable":
        raise CheckFailed(step, f"HTTP {response.status_code} ({code}) : 422 attendu.")
    if "example.invalid" in response.text:
        raise CheckFailed(step, "La réponse recopie le lien envoyé.")
    print(f"    refus 422 en {time.monotonic() - began:.1f} s, sans écho", flush=True)


async def check_gap(run: Run, st: Capture) -> None:
    step = "écart"
    gap: dict[str, Any] = {}

    async def ready() -> bool:
        gap.update(await expect_ok(run, step, "GET", f"/postings/{st.posting_id}/gap"))
        if gap["status"] == "failed":
            raise CheckFailed(step, f"Écart de l'offre {st.posting_id} en échec.")
        return bool(gap["status"] == "ready")

    await within(run, POSTING_S).until(step, ready, "écart jamais prêt")
    score = gap["score"]
    if score is None or not 0 <= score <= 100:
        raise CheckFailed(step, f"Score d'écart hors de 0 à 100 ({st.posting_id}).")
    to_add = [row for row in gap["rows"] if row["action"] == "to_add"]
    if not to_add:
        raise CheckFailed(step, f"Aucune ligne « à ajouter » ({st.posting_id}).")
    top = await expect_ok(run, step, "GET", "/gap/top-missing")
    if not top:
        raise CheckFailed(step, "Aucune compétence qui manque le plus souvent.")
    print(
        f"    score {score} : {len(gap['rows'])} ligne(s) dont {len(to_add)} à ajouter ; "
        f"{len(top)} compétence(s) qui manquent le plus souvent",
        flush=True,
    )
