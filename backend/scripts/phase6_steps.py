"""Étapes « profil » et « design » du contrôle de la phase 6 (`check_phase6`) : le profil maître
tiré du CV fictif puis validé, et le modèle de CV capturé (ressemblance, passes, écarts de police)
puis validé. Relançable : un profil validé ou un modèle prêt est relu au lieu d'être refait (sauf
`fresh`). Rien de ce qui est envoyé ou reçu n'apparaît dans un message d'échec ni dans la sortie :
seulement des étapes, des nombres, des codes et des identifiants."""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from scripts.phase4_steps import CheckFailed, Run, expect_ok, wait_question
from scripts.phase6_rules import check_profile_facts, skills_below_declared
from scripts.sample_cv import make_cv_pdf

PROFILE_S = 180.0  # brouillon du profil en 3 minutes au plus
DESIGN_S = 600.0  # question du modèle en 10 minutes au plus
MAX_PASSES = 3
NOTE = "Note du contrôle de la phase 6 : rien à ajouter au CV."
TEMPLATE_NAME = "Modèle du contrôle de phase 6"
SUBSTITUTE = "Liberation Sans"  # Helvetica du CV fictif n'est pas libre
DEAD = ("failed", "cancelled")


@dataclass
class Capture:
    """Ce que les étapes se passent, et si elles relisent au lieu de refaire."""

    fresh: bool = False
    posting_id: str = ""


def pdf_file(field: str) -> dict[str, tuple[str, bytes, str]]:
    return {field: ("cv-controle.pdf", make_cv_pdf(), "application/pdf")}


def within(run: Run, seconds: float) -> Run:
    """Un passage borné à `seconds` (sans dépasser le délai total restant)."""
    left = run.timeout_s - (time.monotonic() - run.started)
    return Run(run.client, run.events, max(0.0, min(seconds, left)))


async def cost_of(run: Run, step: str, session_id: str) -> str:
    view = await expect_ok(run, step, "GET", f"/sessions/{session_id}")
    tokens = int(view["tokens_in"]) + int(view["tokens_out"])
    return f"{float(view['cost_usd']):.4f} $ ({tokens} tokens)"


async def wait_session(run: Run, step: str, session_id: str, what: str) -> None:
    """Attend la fin réussie de la session ; échec (avec son code) si elle s'arrête autrement."""

    async def done() -> bool:
        view = await expect_ok(run, step, "GET", f"/sessions/{session_id}")
        if view["status"] in DEAD:
            code = (view.get("error") or {}).get("code", "aucun")
            raise CheckFailed(step, f"Session {session_id} arrêtée ({view['status']}, {code}).")
        return bool(view["status"] == "completed")

    await run.until(step, done, what)


async def started_or_running(
    run: Run, step: str, path: str, files: dict[str, Any], data: dict[str, str]
) -> dict[str, Any]:
    """Lance une capture ; une capture déjà en cours (409) est reprise par sa session."""
    try:
        response = await run.client.post(f"/api/v1{path}", files=files, data=data)
    except httpx.HTTPError as exc:
        raise CheckFailed(step, f"API injoignable ({type(exc).__name__}).") from None
    body: dict[str, Any] = response.json()
    if response.status_code == 409 and body["error"]["code"] == "capture_in_progress":
        return {"session_id": body["error"]["details"]["session_id"]}
    if response.status_code != 202:
        code = (body.get("error") or {}).get("code", "sans code")
        raise CheckFailed(step, f"POST {path} : HTTP {response.status_code} ({code}).")
    return body


async def _check_validated(run: Run, step: str, data: dict[str, Any]) -> None:
    check_profile_facts(step, data)
    graph = await expect_ok(run, step, "GET", "/skills/graph")
    skills_below_declared(step, [s["name"] for s in data.get("skills", [])], graph["nodes"])


async def _import_profile(run: Run, step: str) -> dict[str, Any]:
    began = time.monotonic()
    started = await started_or_running(run, step, "/profile/import", pdf_file("cv"), {"note": NOTE})
    sid = str(started["session_id"])
    await wait_session(within(run, PROFILE_S), step, sid, "brouillon du profil jamais prêt")
    seconds = time.monotonic() - began
    draft = (await expect_ok(run, step, "GET", "/profile"))["draft"]
    if not draft:
        raise CheckFailed(step, f"Aucun brouillon après la capture {sid}.")
    data = draft["data"]
    check_profile_facts(step, data)
    print(
        f"    brouillon en {seconds:.0f} s : {len(data['experiences'])} expérience(s), "
        f"{len(data['skills'])} compétence(s), {len(draft['dropped'])} ligne(s) retirée(s), "
        f"résumé {'gardé' if data.get('summary') else 'absent'} ; "
        f"{await cost_of(run, step, sid)}",
        flush=True,
    )
    body = {"data": data, "base_version": draft["version"]}
    saved = await expect_ok(run, step, "PUT", "/profile", json=body)
    if saved["status"] != "validated":
        raise CheckFailed(step, f"Version {saved['version']} non validée.")
    return dict(saved["data"])


async def check_profile(run: Run, st: Capture) -> None:
    step = "profil"
    state = await expect_ok(run, step, "GET", "/profile")
    validated = state.get("validated")
    if validated and not st.fresh:
        await _check_validated(run, step, validated["data"])
        print(f"    profil déjà validé (version {validated['version']}) : relu", flush=True)
        return
    await _check_validated(run, step, await _import_profile(run, step))


def _check_template(step: str, template: dict[str, Any]) -> None:
    if template["score"] is None or not 0 <= template["score"] <= 100:
        raise CheckFailed(step, f"Modèle {template['id']} sans score de ressemblance.")
    if not 1 <= template["passes"] <= MAX_PASSES:
        raise CheckFailed(step, f"{template['passes']} passes : {MAX_PASSES} au plus.")
    if not any(SUBSTITUTE in gap for gap in template["font_gaps"]):
        raise CheckFailed(step, "Écart de police non dit (Helvetica remplacée).")


async def _ready_template(run: Run, step: str, template_id: str) -> dict[str, Any]:
    found: dict[str, Any] = {}

    async def ready() -> bool:
        found.update(await expect_ok(run, step, "GET", f"/cv/templates/{template_id}"))
        if found["status"] == "failed":
            raise CheckFailed(step, f"Modèle {template_id} en échec.")
        return bool(found["status"] == "ready")

    await within(run, 60).until(step, ready, "modèle jamais prêt après « Valider »")
    return found


async def _capture_template(run: Run, step: str) -> dict[str, Any]:
    began = time.monotonic()
    data = {"name": TEMPLATE_NAME}
    started = await started_or_running(run, step, "/cv/templates", pdf_file("file"), data)
    sid = str(started["session_id"])
    listed = await expect_ok(run, step, "GET", "/cv/templates")
    template_id = started.get("template_id") or next(
        (t["id"] for t in listed if t["status"] == "capturing"), ""
    )
    question = await wait_question(within(run, DESIGN_S), step, sid, "cv_template")
    seconds = time.monotonic() - began
    template = await expect_ok(run, step, "GET", f"/cv/templates/{template_id}")
    if template["score"] is None or f"{template['score']} %" not in question.get("question", ""):
        raise CheckFailed(step, f"Score de ressemblance non affiché ({template_id}).")
    body = {"interrupt_id": question["interrupt_id"], "value": "validate"}
    await expect_ok(run, step, "POST", f"/sessions/{sid}/resume", json=body)
    template = await _ready_template(run, step, template_id)
    print(
        f"    question en {seconds:.0f} s : ressemblance {template['score']} % en "
        f"{template['passes']} passe(s), {len(template['font_gaps'])} écart(s) de police ; "
        f"{await cost_of(run, step, sid)}",
        flush=True,
    )
    return template


async def check_design(run: Run, st: Capture) -> None:
    step = "design"
    listed = await expect_ok(run, step, "GET", "/cv/templates")
    ready = next((t for t in listed if t["status"] == "ready" and t["active"]), None)
    if ready and not st.fresh:
        template = await expect_ok(run, step, "GET", f"/cv/templates/{ready['id']}")
        print(f"    modèle déjà prêt ({template['score']} %) : relu", flush=True)
    else:
        template = await _capture_template(run, step)
    _check_template(step, template)


type Step = Callable[[Run, Capture], Awaitable[None]]
