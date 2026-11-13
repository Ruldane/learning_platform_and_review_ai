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
    norm_skill,
    read_states,
)
from scripts.phase5_steps import Etude, around

HISTORY_WEEKS = 12


async def map_before(run: Run, st: Etude) -> None:
    """La carte avant la session : niveau et preuves des compétences de chaque module qui a une
    leçon prête (le quiz peut porter sur un autre module que la session)."""
    program = await expect_ok(run, "carte avant", "GET", f"/programs/{run.program_id}")
    for module_id in dict.fromkeys(st.lessons.values()):
        st.module_skills[module_id] = module_skill_names(program, module_id, "carte avant")
    graph = await expect_ok(run, "carte avant", "GET", "/skills/graph")
    names = [name for skills in st.module_skills.values() for name in skills]
    st.before = read_states(graph, names)


async def map_after(run: Run, st: Etude) -> None:
    """La carte après la session et le quiz ; `valide` seulement si le quiz est réussi (une
    seule passe suffit rarement : un nouvel essai ne vient qu'à J+2)."""
    graph = await expect_ok(run, "carte après", "GET", "/skills/graph")
    after = read_states(graph, [name for skills in st.module_skills.values() for name in skills])
    studied = {norm_skill(name) for name in st.skills}
    quiz_skills = st.module_skills.get(st.quiz_module_id or st.module_id, [])
    validated = {norm_skill(name) for name in quiz_skills} if st.passed else set()
    check_states("carte après", st.before, after, studied=studied, validated=validated)
    for key in [key for key in after if key in studied or key in validated]:
        detail = await expect_ok(run, "carte après", "GET", f"/skills/{after[key].skill_id}")
        check_detail(
            "carte après",
            detail,
            study_id=st.study_id if key in studied else None,
            quiz_id=st.quiz_id if key in validated else None,
        )

    async def read() -> dict[str, Any]:
        found: dict[str, Any] = await expect_ok(
            run, "carte après", "GET", "/skills/history", params={"weeks": HISTORY_WEEKS}
        )
        return found

    history, days = await around(run, "carte après", read, 0)
    mondays = {day - timedelta(days=day.weekday()) for day in days}
    check_history("carte après", history, mondays, len(studied))
    levels = sorted({after[key].level or "aucun" for key in studied})
    gained = sum(after[key].evidence - st.before[key].evidence for key in studied | validated)
    print(
        f"    {len(studied)} compétence(s) du module : niveau {'/'.join(levels)}, "
        f"{gained:+d} preuve(s) en tout",
        flush=True,
    )
    if not st.passed:
        print(
            "    `valide` non attendu : "
            + (
                "quiz bloqué, aucune tentative"
                if st.quiz_blocked
                else "quiz sous 80 % en une passe"
            )
            + f" ; nouvel essai à J+2 ({st.retry_on}), le relancer alors lit les bonnes "
            "réponses de la tentative précédente.",
            flush=True,
        )
