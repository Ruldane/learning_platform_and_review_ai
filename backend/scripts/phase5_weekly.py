"""Étapes « bilan hebdomadaire » et « journal » du contrôle de fin de phase 5 (F13, F18).

Le bilan se règle sur l'heure locale (jour d'aujourd'hui, heure moins une minute) : la tâche
planifiée, qui passe toutes les 15 minutes, doit écrire l'entrée `weekly_review` et lancer une
session `replan` en moins de 16 minutes. Les réglages de January sont remis comme avant, quoi
qu'il arrive. La session lancée n'est pas menée à bout : elle est annulée (rien n'est accepté).
Rien de ce qui est reçu n'apparaît dans la sortie : seulement des étapes, des nombres, des codes
et des identifiants."""

import asyncio
import time
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase5_plan_rules import (
    WEEKLY_LAUNCH_S,
    JournalWant,
    check_journal,
    local_target,
    review_blocker,
)
from scripts.phase5_steps import Etude

STEP = "bilan hebdomadaire"
POLL_WEEKLY_S = 5.0  # la tâche passe toutes les 15 minutes : inutile d'interroger plus vite
JOURNAL_PAGE = 100
JOURNAL_PAGES = 10
OPEN = ("running", "waiting_user", "paused")


def local_now(zone: str) -> datetime:
    """L'heure locale de January (les tests la figent)."""
    return datetime.now(ZoneInfo(zone))


async def journal_entries(run: Run, step: str, kind: str | None = None) -> list[dict[str, Any]]:
    """Les entrées du journal, les plus récentes d'abord (jusqu'à 1 000)."""
    found: list[dict[str, Any]] = []
    before: str | None = None
    for _ in range(JOURNAL_PAGES):
        params: dict[str, Any] = {"limit": JOURNAL_PAGE}
        if kind:
            params["kind"] = kind
        if before:
            params["before"] = before
        page = await expect_ok(run, step, "GET", "/journal", params=params)
        found += page["entries"]
        before = page["next_before"]
        if not before:
            break
    return found


async def _replans(run: Run) -> dict[str, dict[str, Any]]:
    """Les sessions `replan` du programme, par identifiant."""
    sessions = await expect_ok(run, STEP, "GET", "/sessions", params={"graph": "replan"})
    return {s["id"]: s for s in sessions if s["subject_id"] == run.program_id}


def _instant(raw: str) -> datetime:
    moment = datetime.fromisoformat(raw)
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


async def _put(run: Run, settings: dict[str, Any]) -> None:
    await expect_ok(run, STEP, "PUT", "/settings", json=settings)


async def _wait_launch(
    run: Run, known: set[str], seen: set[str], target: date
) -> tuple[dict[str, Any], dict[str, Any]]:
    """L'entrée du bilan et la session `replan` lancées pour lui, au plus 16 minutes plus tard."""
    deadline = time.monotonic() + WEEKLY_LAUNCH_S
    while True:
        reviews = await journal_entries(run, STEP, "weekly_review")
        fresh = [e for e in reviews if e["id"] not in known]
        sessions = [s for sid, s in (await _replans(run)).items() if sid not in seen]
        if fresh and sessions:
            return fresh[0], sessions[0]
        if time.monotonic() > deadline or time.monotonic() - run.started > run.timeout_s:
            what = "entrée" if not fresh else "session `replan`"
            raise CheckFailed(STEP, f"Aucune {what} en {WEEKLY_LAUNCH_S:.0f} s ({target}).")
        await asyncio.sleep(POLL_WEEKLY_S)


async def _cancel(run: Run, session: dict[str, Any]) -> None:
    view = await expect_ok(run, STEP, "GET", f"/sessions/{session['id']}")
    if view["status"] in OPEN:
        await expect_ok(run, STEP, "POST", f"/sessions/{session['id']}/cancel")


async def _already_written(run: Run, st: Etude, replans: set[str]) -> None:
    """Le bilan d'aujourd'hui est déjà dans le journal (un passage plus tôt dans la journée, ou le
    vrai bilan) : la tâche ne l'écrit qu'une fois, le contrôle ne peut pas le rejouer. Il suffit
    alors qu'une session `replan` ait été lancée pour ce programme."""
    if not replans:
        raise CheckFailed(STEP, "Bilan du jour déjà écrit, mais aucune session `replan` lancée.")
    st.review_entry_id = None
    print(
        "    bilan du jour déjà écrit : lancement non rejoué (relancer demain pour le rejouer)",
        flush=True,
    )


async def weekly_review(run: Run, st: Etude) -> None:
    settings = await expect_ok(run, STEP, "GET", "/settings")
    program = await expect_ok(run, STEP, "GET", f"/programs/{run.program_id}")
    target = local_now(settings["timezone"])
    day, hour = local_target(target)
    starts = [date.fromisoformat(week["start_date"]) for week in program["weeks"]]
    if blocker := review_blocker(starts, target.date()):
        raise CheckFailed(STEP, blocker)
    reviews = await journal_entries(run, STEP, "weekly_review")
    known, seen = {e["id"] for e in reviews}, set(await _replans(run))
    if any(e["occurred_on"] == target.date().isoformat() for e in reviews):
        await _already_written(run, st, seen)
        return
    changed = settings | {"weekly_review": {"day": day, "time": hour}}
    put_at = datetime.now(UTC)
    await _put(run, changed)
    try:
        entry, session = await _wait_launch(run, known, seen, target.date())
    finally:
        await _put(run, settings)
    delay = (_instant(session["created_at"]) - put_at).total_seconds()
    if delay > WEEKLY_LAUNCH_S:
        raise CheckFailed(STEP, f"Session {session['id']} lancée {delay:.0f} s après le réglage.")
    st.review_entry_id = entry["id"]
    await _cancel(run, session)
    print(
        f"    bilan {entry['id']} et session {session['id']} en {max(delay, 0):.0f} s", flush=True
    )


async def check_journal_step(run: Run, st: Etude) -> None:
    """Une entrée de chaque genre, reliée à ce que ce passage a fait."""
    entries = await journal_entries(run, "journal")
    want = JournalWant(st.study_id, st.attempt_id, st.review_entry_id, list(st.captures))
    check_journal(entries, want)
    kinds = sorted({e["kind"] for e in entries})
    print(f"    {len(entries)} entrée(s) : {', '.join(kinds)}", flush=True)
