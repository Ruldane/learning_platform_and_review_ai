"""Carte de compétences (D107) : graphe et radar, détail (preuves structurées et de la phase 4),
prochaine action selon le niveau et ce que la carte lit des autres features."""

from datetime import timedelta

import pytest

from app.core.errors import AppError
from app.core.skills import Evidence
from app.db.models.skills import SkillLevel
from app.features.skills.map import (
    ActionFacts,
    evidence_url,
    next_action,
    skill_detail,
    skill_graph,
)
from tests.features.skills.support import (
    NOW,
    Factory,
    add_card,
    add_edge,
    add_goal,
    add_lesson,
    add_program,
    add_quiz,
    add_skill,
    set_level,
)

ME, OTHER = "moi", "autre"
AT = "2026-11-17T09:00:00+00:00"


def _proof(kind: str, ref_id: str | None, label: str) -> dict[str, object]:
    return {"kind": kind, "ref_id": ref_id, "label": label, "at": AT}


async def test_graph_lists_nodes_edges_and_domains(db_session_factory: Factory) -> None:
    proofs = [_proof("quiz", "q1", "Quiz"), "Programme Data"]
    pandas = await add_skill(db_session_factory, ME, "Pandas", "Données", "valide", proofs)
    numpy = await add_skill(db_session_factory, ME, "NumPy", "Données")
    sql = await add_skill(db_session_factory, ME, "SQL", None, "declare")
    await add_edge(db_session_factory, ME, numpy, pandas)
    await add_skill(db_session_factory, OTHER, "Rust", "Système", "prouve")
    async with db_session_factory() as db:
        graph = await skill_graph(db, ME)
    assert [(n.id, n.name, n.domain, n.level, n.demand, n.evidence_count) for n in graph.nodes] == [
        (numpy, "NumPy", "Données", None, None, 0),
        (pandas, "Pandas", "Données", "valide", None, 2),
        (sql, "SQL", "Autres", "declare", None, 0),
    ]
    assert [(e.before_id, e.after_id) for e in graph.edges] == [(numpy, pandas)]
    # Données : (75 + 0) / 2 = 37,5 → 38 ; Autres : 25.
    assert [(d.domain, d.score) for d in graph.domains] == [("Autres", 25), ("Données", 38)]


async def test_detail_shows_structured_and_legacy_evidence(db_session_factory: Factory) -> None:
    proofs = [
        "Programme Data (phase 4)",
        _proof("quiz", "q1", "Quiz « Bases » : 85 % (17/11)"),
        _proof("study", "s1", "Session « Bases »"),
        _proof("capture", None, "J'ai appris pandas"),
        _proof("lesson", "l1", "Leçon « Bases »"),
        _proof("program", "p1", "Programme P"),
        _proof("cv", None, "CV"),
        {"kind": "inconnu", "label": "ignorée"},
    ]
    skill_id = await add_skill(
        db_session_factory, ME, "Pandas", "Données", "prouve", proofs, synonyms=["pd"]
    )
    async with db_session_factory() as db:
        detail = await skill_detail(db, ME, skill_id, NOW)
    assert (detail.name, detail.domain, detail.synonyms, detail.level) == (
        "Pandas",
        "Données",
        ["pd"],
        "prouve",
    )
    assert [(e.kind, e.url) for e in detail.evidence] == [
        ("cv", None),
        ("program", "/apprendre/programme/p1"),
        ("lesson", "/apprendre/lecons/l1"),
        ("capture", "/etudier/journal"),
        ("study", "/etudier/session/s1"),
        ("quiz", "/etudier/quiz/q1"),
        ("program", None),  # chaîne de la phase 4 : ni référence ni date
    ]
    assert detail.evidence[5].label == "Quiz « Bases » : 85 % (17/11)"
    assert detail.evidence[5].at is not None and detail.evidence[5].at.isoformat() == AT
    assert (
        detail.evidence[-1].at is None and detail.evidence[-1].label == "Programme Data (phase 4)"
    )
    assert detail.postings == [] and detail.next_action is None


async def test_detail_of_another_user_is_404(db_session_factory: Factory) -> None:
    skill_id = await add_skill(db_session_factory, OTHER, "Pandas", "Données", "valide")
    async with db_session_factory() as db:
        with pytest.raises(AppError) as caught:
            await skill_detail(db, ME, skill_id, NOW)
    assert (caught.value.code, caught.value.status_code) == ("skill_not_found", 404)


BASES = ActionFacts(module="Bases", lesson_id="L1", quiz_id="Q1")


@pytest.mark.parametrize(
    ("level", "facts", "expected"),
    [
        (None, BASES, ("study", "Étudier « Bases »", "/etudier/session?lecon=L1")),
        ("declare", ActionFacts(), ("study", "Étudier « Pandas »", "/etudier/session")),
        ("en_cours", BASES, ("quiz", "Passer le quiz « Bases »", "/etudier/quiz/Q1")),
        (
            "en_cours",
            ActionFacts(module="Bases"),
            ("quiz", "Passer le quiz « Bases »", "/etudier/quiz"),
        ),
        (
            "valide",
            ActionFacts(cards_due=True),
            ("review", "Réviser les fiches « Pandas »", "/etudier/revisions"),
        ),
        ("valide", ActionFacts(), ("project", "Projet preuve (bientôt)", None)),
        ("prouve", BASES, None),
    ],
)
def test_next_action_by_level(
    level: SkillLevel | None, facts: ActionFacts, expected: tuple[str, str, str | None] | None
) -> None:
    action = next_action(level, "Pandas", facts)
    assert (None if action is None else (action.kind, action.label, action.url)) == expected


def test_evidence_url_escapes_reference() -> None:
    item = Evidence(kind="quiz", ref_id="a/../b", label="Quiz", at="")
    assert evidence_url(item) == "/etudier/quiz/a%2F..%2Fb"


async def test_detail_next_action_reads_lesson_quiz_and_due_cards(
    db_session_factory: Factory,
) -> None:
    """La carte lit le module validé qui enseigne la compétence (pas un brouillon ni un module
    sauté), sa leçon et son quiz prêts, et les fiches dues aujourd'hui (jour de Paris)."""
    draft_goal = await add_goal(db_session_factory, ME)
    await add_program(
        db_session_factory, ME, draft_goal, [("Brouillon", ["pandas"])], status="draft"
    )
    goal = await add_goal(db_session_factory, ME)
    rows = await add_program(
        db_session_factory, ME, goal, [("Sauté", ["Pandas"]), ("Bases", ["SQL", "pandas"])],
        skipped=[0], created=NOW - timedelta(days=1),
    )  # fmt: skip
    lesson_id = await add_lesson(db_session_factory, ME, rows, 1)
    quiz_id = await add_quiz(db_session_factory, ME, rows, 1)
    skill_id = await add_skill(db_session_factory, ME, "Pandas", "Données", "declare")

    async def action() -> tuple[str, str, str | None] | None:
        async with db_session_factory() as db:
            found = (await skill_detail(db, ME, skill_id, NOW)).next_action
        return None if found is None else (found.kind, found.label, found.url)

    assert await action() == ("study", "Étudier « Bases »", f"/etudier/session?lecon={lesson_id}")
    await set_level(db_session_factory, ME, skill_id, "en_cours")
    assert await action() == ("quiz", "Passer le quiz « Bases »", f"/etudier/quiz/{quiz_id}")
    await set_level(db_session_factory, ME, skill_id, "valide")
    await add_card(db_session_factory, ME, "PANDAS ", NOW.date() + timedelta(days=1))
    await add_card(db_session_factory, OTHER, "pandas", NOW.date())
    assert await action() == ("project", "Projet preuve (bientôt)", None)
    await add_card(db_session_factory, ME, "Pandas", NOW.date())
    assert await action() == ("review", "Réviser les fiches « Pandas »", "/etudier/revisions")


async def test_study_action_without_ready_lesson_opens_study_home(
    db_session_factory: Factory,
) -> None:
    goal = await add_goal(db_session_factory, ME)
    rows = await add_program(db_session_factory, ME, goal, [("Bases", ["pandas"])])
    await add_lesson(db_session_factory, ME, rows, 0, status="generating")
    await add_quiz(db_session_factory, ME, rows, 0, status="generating")
    skill_id = await add_skill(db_session_factory, ME, "Pandas", None, "declare")
    async with db_session_factory() as db:
        study = (await skill_detail(db, ME, skill_id, NOW)).next_action
    await set_level(db_session_factory, ME, skill_id, "en_cours")
    async with db_session_factory() as db:
        quiz = (await skill_detail(db, ME, skill_id, NOW)).next_action
    assert study is not None and (study.label, study.url) == (
        "Étudier « Bases »",
        "/etudier/session",
    )
    assert quiz is not None and quiz.url == "/etudier/quiz"
