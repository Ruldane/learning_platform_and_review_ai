"""Comparaison avec le poste cible (D107 n° 2) : compétences du programme de l'objectif, cible
`valide`, écart de rang et couverture."""

from datetime import timedelta

import pytest

from app.core.errors import AppError
from app.features.skills.compare import compare_with_goal, gap
from tests.features.skills.support import (
    NOW,
    Factory,
    add_goal,
    add_program,
    add_skill,
)

ME, OTHER = "moi", "autre"


async def test_compare_goal_targets_valide_with_coverage(db_session_factory: Factory) -> None:
    goal = await add_goal(
        db_session_factory, ME, target_role="Data engineer", created=NOW - timedelta(days=2)
    )
    await add_program(
        db_session_factory, ME, goal,
        [("Bases", ["pandas", "NumPy"]), ("SQL", ["SQL", "Pandas"]), ("Git", ["Git"])],
        status="draft", skipped=[2],
    )  # fmt: skip
    await add_goal(db_session_factory, ME)  # plus récent, sans programme : ignoré par défaut
    pandas = await add_skill(db_session_factory, ME, "Pandas", "Données", "valide")
    numpy = await add_skill(db_session_factory, ME, "NumPy", "Données", "en_cours")
    sql = await add_skill(db_session_factory, ME, "SQL", None)
    git = await add_skill(db_session_factory, ME, "Git", "Outils", "prouve")
    await add_skill(db_session_factory, ME, "Rust", "Système", "declare")  # hors programme
    async with db_session_factory() as db:
        default = await compare_with_goal(db, ME, None)
        chosen = await compare_with_goal(db, ME, goal)
    assert default == chosen
    assert (default.target_label, default.coverage) == ("Data engineer", 50)
    assert [(r.skill_id, r.name, r.domain, r.mine, r.target, r.gap) for r in default.rows] == [
        (pandas, "Pandas", "Données", "valide", "valide", 0),
        (numpy, "NumPy", "Données", "en_cours", "valide", 1),
        (sql, "SQL", "Autres", None, "valide", 3),
        (git, "Git", "Outils", "prouve", "valide", -1),
    ]


async def test_compare_label_falls_back_to_goal_text(db_session_factory: Factory) -> None:
    goal = await add_goal(db_session_factory, ME)
    await add_program(db_session_factory, ME, goal, [("Bases", [])])
    async with db_session_factory() as db:
        out = await compare_with_goal(db, ME, None)
    assert (out.target_label, out.coverage, out.rows) == ("Devenir data engineer", 0, [])


async def test_compare_without_target_or_with_foreign_goal_is_404(
    db_session_factory: Factory,
) -> None:
    mine = await add_goal(db_session_factory, ME)  # sans programme
    theirs = await add_goal(db_session_factory, OTHER)
    await add_program(db_session_factory, OTHER, theirs, [("Bases", ["pandas"])])
    codes = []
    for goal_id in (None, mine, theirs):
        async with db_session_factory() as db:
            with pytest.raises(AppError) as caught:
                await compare_with_goal(db, ME, goal_id)
        codes.append((caught.value.code, caught.value.status_code))
    assert codes == [
        ("no_compare_target", 404),
        ("no_compare_target", 404),
        ("goal_not_found", 404),
    ]


def test_gap_counts_absent_as_minus_one() -> None:
    assert [gap(level, "valide") for level in (None, "declare", "valide", "prouve")] == [
        3,
        2,
        0,
        -1,
    ]
