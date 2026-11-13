"""Étape « replanification » du contrôle de fin de phase 5 : « cette semaine je n'ai que 5 heures »
(F13). Le Stratège propose, le code range sous les plafonds, January accepte : la proposition
`pending` montre un avant / après sous 255 minutes pour la semaine plafonnée, l'acceptation la rend
`accepted` et passe le programme à la version suivante. Rien de ce qui est reçu n'apparaît dans
la sortie : seulement des étapes, des nombres, des codes et des identifiants."""

from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase5_drive import DEAD, resume
from scripts.phase5_plan_rules import (
    REPLAN_MESSAGE,
    WEEK_MINUTES,
    capped_start,
    check_accepted,
    check_pending,
    feasible_minutes,
    week_cap,
)
from scripts.phase5_rules import option_value
from scripts.phase5_steps import Etude, local_today

STEP = "replanification"
ACCEPT = "accept_replan"


async def _versions(run: Run) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = await expect_ok(
        run, STEP, "GET", f"/programs/{run.program_id}/versions"
    )
    return found


async def _wait_proposal(run: Run, session_id: str) -> dict[str, Any]:
    """La question d'acceptation ; si la session s'arrête avant, la dernière version dit pourquoi
    (`empty` : rien à changer, `impossible` : la semaine ne tient pas une pratique et le quiz)."""
    pending: dict[str, Any] = {}

    async def asked() -> bool:
        view = await expect_ok(run, STEP, "GET", f"/sessions/{session_id}")
        done = view["status"] in (*DEAD, "completed")
        if done:
            newest = (await _versions(run) or [{}])[0]
            raise CheckFailed(
                STEP, f"Session {session_id} arrêtée ({view['status']}) sans proposition à "
                f"accepter ; dernière version : {newest.get('version')} {newest.get('status')}."
            )  # fmt: skip
        question = view.get("pending_interrupt") or {}
        if view["status"] == "waiting_user" and question.get("kind") == ACCEPT:
            pending.update(question)
            return True
        return False

    await run.until(STEP, asked, "proposition jamais faite")
    return pending


async def _wait_completed(run: Run, session_id: str) -> None:
    async def completed() -> bool:
        view = await expect_ok(run, STEP, "GET", f"/sessions/{session_id}")
        if view["status"] in DEAD:
            code = (view.get("error") or {}).get("code", "aucun")
            raise CheckFailed(STEP, f"Session {session_id} arrêtée ({view['status']}, {code}).")
        return bool(view["status"] == "completed")

    await run.until(STEP, completed, "replanification jamais finie")


async def replan_week(run: Run, st: Etude) -> None:
    before = await expect_ok(run, STEP, "GET", f"/programs/{run.program_id}")
    minutes = feasible_minutes(before, await local_today(run, STEP))
    message = REPLAN_MESSAGE
    if minutes != WEEK_MINUTES:  # la session du contrôle remplit déjà la semaine
        message = f"cette semaine je n'ai que {minutes} minutes"
        print(
            f"    5 heures ne tiennent plus (minutes déjà faites) : {minutes} minutes demandées",
            flush=True,
        )
    cap_week = week_cap(minutes)
    body = {"available_minutes": minutes, "message": message}
    started = await expect_ok(run, STEP, "POST", f"/programs/{run.program_id}/replan", json=body)
    session_id = str(started["session_id"])
    question = await _wait_proposal(run, session_id)
    proposal = (await _versions(run))[0]
    check_pending(proposal, before, session_id, cap_week)
    unchanged = await expect_ok(run, STEP, "GET", f"/programs/{run.program_id}")
    if unchanged["version"] != before["version"]:
        raise CheckFailed(STEP, "Le programme a changé avant l'acceptation.")
    await resume(run, STEP, session_id, question, option_value(question, "accept", step=STEP))
    await _wait_completed(run, session_id)
    after = await expect_ok(run, STEP, "GET", f"/programs/{run.program_id}")
    accepted = (await _versions(run))[0]
    check_accepted(
        accepted,
        after,
        before=int(before["version"]),
        capped=capped_start(proposal, cap_week),
        cap_week=cap_week,
    )
    st.program_version = int(after["version"])
    moved = len(proposal["diff"]["moved"])
    print(
        f"    version {before['version']} -> {after['version']} : {moved} tâche(s) déplacée(s), "
        f"{len(proposal['diff']['removed'])} retirée(s), {len(proposal['diff']['added'])} "
        "ajoutée(s)", flush=True,
    )  # fmt: skip
