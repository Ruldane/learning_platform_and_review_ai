"""Mener une session d'agents jusqu'à sa fin en répondant à ses questions (contrôle de fin de
phase 5) : la capture rapide et la replanification s'y prêtent. Rien de ce qui est envoyé ou reçu
n'apparaît dans un message d'échec : seulement des étapes, des codes et des identifiants."""

import time
from collections.abc import Callable, Mapping
from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok

DEAD = ("failed", "cancelled")
OPEN = ("running", "waiting_user", "paused")
type Answer = Callable[[dict[str, Any]], Any]


async def resume(
    run: Run, step: str, session_id: str, question: dict[str, Any], value: Any
) -> None:
    body = {"interrupt_id": question["interrupt_id"], "value": value}
    await expect_ok(run, step, "POST", f"/sessions/{session_id}/resume", json=body)


async def drive(
    run: Run, step: str, session_id: str, answers: Mapping[str, Answer]
) -> list[tuple[str, float]]:
    """Répond à chaque question de la session (`answers` : genre de question -> fonction qui rend
    la valeur de la réponse) jusqu'à ce qu'elle soit `completed` ; rend les genres posés, dans
    l'ordre, avec les secondes écoulées depuis l'appel. Une question d'un autre genre, ou une
    session arrêtée, est un échec."""
    started = time.monotonic()
    seen: set[str] = set()
    asked: list[tuple[str, float]] = []

    async def finished() -> bool:
        view = await expect_ok(run, step, "GET", f"/sessions/{session_id}")
        if view["status"] == "completed":
            return True
        if view["status"] in DEAD:
            code = (view.get("error") or {}).get("code", "aucun")
            raise CheckFailed(step, f"Session {session_id} arrêtée ({view['status']}, {code}).")
        question = view.get("pending_interrupt") or {}
        if view["status"] != "waiting_user" or question.get("interrupt_id") in seen:
            return False
        seen.add(question["interrupt_id"])
        kind = str(question.get("kind"))
        if kind not in answers:
            raise CheckFailed(step, f"Question « {kind} » inattendue (session {session_id}).")
        asked.append((kind, time.monotonic() - started))
        await resume(run, step, session_id, question, answers[kind](question))
        return False

    await run.until(step, finished, f"session {session_id} jamais finie")
    return asked


async def close_open_replans(run: Run, step: str) -> int:
    """Annule les replanifications ouvertes du programme (une proposition laissée en attente par
    un passage interrompu bloque la suivante : 409 `replan_open`) ; rend leur nombre. Une
    proposition en attente est de toute façon remplacée par la suivante (D106)."""
    sessions = await expect_ok(run, step, "GET", "/sessions", params={"graph": "replan"})
    opened = [s for s in sessions if s["subject_id"] == run.program_id and s["status"] in OPEN]
    for session in opened:
        await expect_ok(run, step, "POST", f"/sessions/{session['id']}/cancel")
    if opened:
        ids = ", ".join(s["id"] for s in opened)
        print(
            f"    {len(opened)} replanification(s) restée(s) ouverte(s), annulée(s) : {ids}",
            flush=True,
        )
    return len(opened)
