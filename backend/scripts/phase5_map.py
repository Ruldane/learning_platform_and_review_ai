"""Étapes « carte avant » et « carte après » du contrôle de fin de phase 5 : la session guidée et le
quiz mettent à jour la carte (preuves et niveau des compétences du module, historique de la
semaine en cours, F15, F26). Rien de ce qui est reçu n'apparaît dans la sortie : seulement des
étapes, des nombres, des niveaux (codes) et des identifiants."""

from datetime import timedelta
from typing import Any

from scripts.phase4_steps import Run, expect_ok
from scripts.phase5_map_rules import (
    check_detail,
    check_history,
    check_states,
    module_skill_names,
    read_states,
)
from scripts.phase5_steps import Etude, around

HISTORY_WEEKS = 12


async def map_before(run: Run, st: Etude) -> None:
    """La carte avant la session : niveau et preuves de chaque compétence du module."""
    program = await expect_ok(run, "carte avant", "GET", f"/programs/{run.program_id}")
    st.skills = module_skill_names(program, st.module_id, "carte avant")
    graph = await expect_ok(run, "carte avant", "GET", "/skills/graph")
    st.before = read_states(graph, st.skills)


async def map_after(run: Run, st: Etude) -> None:
    """La carte après la session et le quiz ; `valide` seulement si le quiz est réussi (une
    seule passe suffit rarement : un nouvel essai ne vient qu'à J+2)."""
    graph = await expect_ok(run, "carte après", "GET", "/skills/graph")
    after = read_states(graph, st.skills)
    check_states("carte après", st.before, after, passed=st.passed)
    for state in after.values():
        detail = await expect_ok(run, "carte après", "GET", f"/skills/{state.skill_id}")
        check_detail(
            "carte après", detail, study_id=st.study_id, quiz_id=st.quiz_id, passed=st.passed
        )

    async def read() -> dict[str, Any]:
        found: dict[str, Any] = await expect_ok(
            run, "carte après", "GET", "/skills/history", params={"weeks": HISTORY_WEEKS}
        )
        return found

    history, days = await around(run, "carte après", read, 0)
    mondays = {day - timedelta(days=day.weekday()) for day in days}
    check_history("carte après", history, mondays, len(st.skills))
    levels = sorted({s.level or "aucun" for s in after.values()})
    gained = sum(
        new.evidence - old.evidence
        for old, new in zip(st.before.values(), after.values(), strict=True)
    )
    print(f"    {len(st.skills)} compétence(s) du module : niveau {'/'.join(levels)}, "
          f"{gained:+d} preuve(s) en tout", flush=True)  # fmt: skip
    if not st.passed:
        print(
            "    `valide` non atteint : quiz sous 80 % en une passe ; un nouvel essai ne vient "
            f"qu'à J+2 ({st.retry_on}), relancer le contrôle alors répond avec les "
            "bonnes réponses de la tentative précédente.", flush=True,
        )  # fmt: skip
