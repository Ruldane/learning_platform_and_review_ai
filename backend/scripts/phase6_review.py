"""Étapes 7 à 11 du contrôle de la phase 6 (`check_phase6`, parties `revue` et `tout`) : la revue du
CV contre l'offre fictive, les décisions, « Générer le PDF » (rendu réel), deux générations
simultanées, « Terminer ». Relançable : une revue ouverte sur l'offre est reprise (409
`review_in_progress`), une revue close laisse place à une nouvelle revue sur la même offre. Rien
de ce qui est envoyé ou reçu n'apparaît dans un message d'échec ni dans la sortie : seulement des
étapes, des nombres, des codes et des identifiants."""

import asyncio
import time
from typing import Any

import httpx

from scripts.phase4_steps import API, CheckFailed, Run, expect_ok, wait_question
from scripts.phase6_review_rules import (
    check_bulk,
    check_decided,
    check_proposals,
    check_version,
    pick_refusal,
    profile_text,
)
from scripts.phase6_steps import Capture, cost_of, within

REVIEW_S = 900.0  # la question « Que veux-tu maintenant ? » en 15 minutes au plus
RENDER_S = 300.0  # un PDF en 5 minutes au plus
CLOSE_S = 60.0
BULK_MAX = 50
GEN_CODES = ("generation_in_progress", "review_not_waiting")


def _code(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["code"])
    except (ValueError, KeyError, TypeError):
        return "sans code"


async def _send(
    run: Run, step: str, path: str, body: dict[str, Any] | None = None
) -> httpx.Response:
    try:
        return await run.client.post(f"{API}{path}", json=body)
    except httpx.HTTPError as exc:
        raise CheckFailed(step, f"API injoignable ({type(exc).__name__}).") from None


async def _review(run: Run, step: str, review_id: str) -> dict[str, Any]:
    review: dict[str, Any] = await expect_ok(run, step, "GET", f"/cv/reviews/{review_id}")
    return review


async def _start(run: Run, step: str, posting_id: str) -> tuple[str, str]:
    """La revue lancée, ou celle déjà ouverte sur l'offre : (revue, session)."""
    response = await _send(run, step, "/cv/reviews", {"posting_id": posting_id})
    body = response.json() if response.content else {}
    if response.status_code == 202:
        return str(body["review_id"]), str(body["session_id"])
    if response.status_code == 409 and _code(response) == "review_in_progress":
        review_id = str(body["error"]["details"]["review_id"])
        session_id = (await _review(run, step, review_id))["session_id"]
        if session_id:
            print(f"    revue {review_id} déjà ouverte : reprise", flush=True)
            return review_id, str(session_id)
    raise CheckFailed(step, f"POST /cv/reviews : HTTP {response.status_code} ({_code(response)}).")


async def _waiting(run: Run, step: str, review_id: str, budget: float) -> dict[str, Any]:
    """La revue une fois la question de sortie posée ; échec si elle s'arrête avant."""
    found: dict[str, Any] = {}

    async def ready() -> bool:
        found.update(await _review(run, step, review_id))
        if found["status"] in ("failed", "cancelled"):
            raise CheckFailed(step, f"Revue {review_id} {found['status']}.")
        return bool(found["waiting_output"])

    await within(run, budget).until(step, ready, "question « cv_output » jamais posée")
    return found


async def check_review(run: Run, st: Capture) -> None:
    step = "revue"
    began = time.monotonic()
    st.review_id, st.session_id = await _start(run, step, st.posting_id)
    review = await _waiting(run, step, st.review_id, REVIEW_S)
    st.profile_text = profile_text((await expect_ok(run, step, "GET", "/profile"))["validated"])
    held, gaps, foreign = check_proposals(step, review, st.profile_text)
    seconds = time.monotonic() - began
    print(
        f"    question en {seconds:.0f} s : {len(review['modifications'])} modification(s) dont "
        f"{held} à confirmer, {gaps} terme(s) vers l'écart dont {foreign} absent(s) du profil, "
        f"couverture d'origine "
        f"{review['before']['coverage_percent']} % ; {await cost_of(run, step, st.session_id)}",
        flush=True,
    )


async def check_decisions(run: Run, st: Capture) -> None:
    step = "décisions"
    mods = (await _review(run, step, st.review_id))["modifications"][:BULK_MAX]
    body = {"ids": [m["id"] for m in mods], "status": "accepted"}
    path = f"/cv/reviews/{st.review_id}/modifications"
    result = await expect_ok(run, step, "PATCH", path, json=body)
    check_bulk(step, mods, result)
    target = pick_refusal(step, mods)
    refused = await expect_ok(
        run, step, "PATCH", f"/cv/modifications/{target['id']}", json={"status": "refused"}
    )
    if refused["status"] != "refused":
        raise CheckFailed(step, f"Modification {target['ref']} non refusée.")
    now = await _review(run, step, st.review_id)
    check_decided(step, now, mods, target["id"], st.profile_text)
    print(
        f"    {result['updated']} acceptée(s), {len(result['skipped'])} sautée(s) (à confirmer), "
        f"1 refusée ({target['ref']})",
        flush=True,
    )


async def _generate(run: Run, step: str, review_id: str) -> httpx.Response:
    return await _send(run, step, f"/cv/reviews/{review_id}/generate", {})


async def _rendered(run: Run, step: str, version_id: str) -> dict[str, Any]:
    """La version une fois son rendu fini ; échec si elle n'est pas `ready`."""
    found: dict[str, Any] = {}

    async def done() -> bool:
        found.update(await expect_ok(run, step, "GET", f"/cv/versions/{version_id}"))
        return bool(found["status"] != "rendering")

    await within(run, RENDER_S).until(step, done, "PDF jamais rendu")
    if found["status"] != "ready":
        raise CheckFailed(step, f"Version {version_id} : statut {found['status']}.")
    return found


async def check_generation(run: Run, st: Capture) -> None:
    step = "génération"
    began = time.monotonic()
    review = await _review(run, step, st.review_id)
    started = await _generate(run, step, st.review_id)
    if started.status_code != 202:
        raise CheckFailed(step, f"POST generate : HTTP {started.status_code} ({_code(started)}).")
    version = await _rendered(run, step, started.json()["version_id"])
    pdf = await run.request(step, "GET", f"/cv/versions/{version['id']}/pdf")
    disposition = pdf.headers.get("content-disposition", "")
    ignored = check_version(step, version, review, pdf.content, disposition, st.profile_text)
    await _waiting(run, step, st.review_id, RENDER_S)
    checks = version["indicators"]["checks"]
    print(
        f"    version {version['number']} prête en {time.monotonic() - began:.0f} s : "
        f"{version['page_count']} page(s) comme l'original, {sum(c['passed'] for c in checks)}/"
        f"{len(checks)} contrôles ATS, couverture {review['before']['coverage_percent']} % → "
        f"{version['indicators']['coverage_percent']} %, {ignored} décision(s) ignorée(s)",
        flush=True,
    )


async def check_double(run: Run, st: Capture) -> None:
    step = "double génération"
    first, second = await asyncio.gather(
        _generate(run, step, st.review_id), _generate(run, step, st.review_id)
    )
    codes = sorted([first.status_code, second.status_code])
    if codes != [202, 409]:
        raise CheckFailed(step, f"HTTP {codes[0]} et {codes[1]} : un 202 et un 409 attendus.")
    refused = first if first.status_code == 409 else second
    started = second if refused is first else first
    if _code(refused) not in GEN_CODES:
        raise CheckFailed(step, f"409 `{_code(refused)}` : code inattendu.")
    version = await _rendered(run, step, started.json()["version_id"])
    review = await _waiting(run, step, st.review_id, RENDER_S)
    if len(review["versions"]) != 2:
        raise CheckFailed(step, f"{len(review['versions'])} version(s) : 2 attendues.")
    print(f"    un 202 (version {version['number']}) et un 409 ({_code(refused)})", flush=True)


async def check_finish(run: Run, st: Capture) -> None:
    step = "terminer"
    question = await wait_question(within(run, CLOSE_S), step, st.session_id, "cv_output")
    body = {"interrupt_id": question["interrupt_id"], "value": {"choice": "finish"}}
    await expect_ok(run, step, "POST", f"/sessions/{st.session_id}/resume", json=body)
    found: dict[str, Any] = {}

    async def done() -> bool:
        found.update(await _review(run, step, st.review_id))
        return bool(found["status"] == "done")

    await within(run, CLOSE_S).until(step, done, "revue jamais terminée")
    again = await _generate(run, step, st.review_id)
    if again.status_code != 409 or _code(again) != "review_closed":
        raise CheckFailed(step, f"Génération après « Terminer » : HTTP {again.status_code}.")
    print(f"    revue terminée, {len(found['versions'])} version(s) gardée(s)", flush=True)
