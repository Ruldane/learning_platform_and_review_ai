"""L'Examinateur (SPEC 9.1, F9, D100) écrit le quiz d'un module et note les réponses ouvertes
d'une tentative.

`write` demande un `QuizDraft` et le fait vérifier par `quiz_problems` : les problèmes repartent
au modèle, deux fois au plus (`MAX_QUIZ_ASKS` = une demande et deux re-demandes) ; ensuite le
quiz est déclaré invalide (`failure`) et le parcours le range en échec.

`grade_open` fait une seule demande pour toutes les réponses ouvertes (aucune : pas d'appel).
Chaque réponse est encadrée comme non fiable (`untrusted`, SPEC 17.4), la leçon aussi ; les QCM,
notés par le code, ne sont jamais envoyés au modèle. Une référence inconnue est ignorée, une
question sans note vaut 0 avec `MISSING_FEEDBACK` ; une note hors de {0 ; 0,5 ; 1} est refusée
par le schéma et redemandée.

Aucun de ces nœuds ne touche un port : rejoués, ils redemandent au modèle sans rien écrire."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.examiner_flow import AGENT, Node, attempt_of, material_of
from app.agents.nodes.lesson_common import LANGUAGES
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.quiz import QuizState
from app.agents.tools.quiz_port import (
    GradeDraft,
    Grades,
    GradingItem,
    ModuleMaterial,
    QuizDraft,
    quiz_problems,
)

MAX_QUIZ_ASKS = 3  # une demande + deux re-demandes avec les problèmes de `quiz_problems`
MISSING_FEEDBACK = "Réponse non évaluée : relis la correction."
WRITE_REQUEST = "Écris le quiz du module."
GRADE_REQUEST = "Note les réponses ouvertes."
LESSON_CHARS = 20_000  # une leçon de 2 500 mots tient en entier
MAX_REASON_CHARS = 300  # `quizzes.failure_reason`
WRITE_TIMEOUT_S = 600  # trois demandes d'un quiz complet, avec leurs nouveaux essais
GRADE_TIMEOUT_S = 300

logger = logging.getLogger(__name__)


def _module_prompt(material: ModuleMaterial) -> str:
    """Titre et compétences viennent du programme (sortie d'agent) : donnée encadrée."""
    lines = [
        f"Titre : {material.module_title}",
        f"Compétences : {', '.join(material.skills) or 'aucune précisée'}",
    ]
    return untrusted("\n".join(lines), "module")


def _lesson(markdown: str) -> str:
    return untrusted(markdown[:LESSON_CHARS], "leçon")


def _problems_text(problems: list[str]) -> str:
    return (
        "Ton quiz ne respecte pas les règles :\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + "\nCorrige-le et rends de nouveau le quiz complet."
    )


async def _ask_quiz(deps: GraphDeps, prompt: str) -> tuple[QuizDraft, list[str]]:
    """Une demande, puis deux re-demandes au plus ; rend le dernier brouillon et ses problèmes."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(WRITE_REQUEST)]
    found: QuizDraft | None = None
    problems: list[str] = []
    for ask in range(1, MAX_QUIZ_ASKS + 1):
        if found is not None:
            messages += [AIMessage(found.model_dump_json()), HumanMessage(_problems_text(problems))]
        found = await structured_call(
            model,
            QuizDraft,
            messages,
            agent=AGENT,
            step=f"quiz-{ask}",
            intent="j'écris le quiz du module" if ask == 1 else "je corrige le quiz",
        )
        problems = quiz_problems(found)
        if not problems:
            break
    assert found is not None
    return found, problems


def make_write(deps: GraphDeps) -> Node:
    @node_timeout(WRITE_TIMEOUT_S)
    async def write(state: QuizState) -> QuizState:
        material = material_of(state)
        prompt = render_prompt(
            AGENT,
            mode="write",
            module=_module_prompt(material),
            lesson=_lesson(material.lesson_markdown),
            language=LANGUAGES.get(material.language, material.language),
            min_questions=8,
            max_questions=12,
            min_cards=3,
            max_cards=6,
        )
        draft, problems = await _ask_quiz(deps, prompt)
        if not problems:
            return {"draft": draft.model_dump(mode="json")}
        logger.info(
            "Quiz invalide : session %s, quiz %s, %d problème(s) après %d essais",
            deps.session_id,
            material.quiz_id,
            len(problems),
            MAX_QUIZ_ASKS,
        )
        reason = f"Quiz invalide après {MAX_QUIZ_ASKS} essais : " + " ; ".join(problems)
        return {"draft": None, "failure": reason[:MAX_REASON_CHARS]}

    return write


def route_write(state: QuizState) -> str:
    return "save_quiz" if state.get("draft") else "failed"


def _item_prompt(item: GradingItem) -> str:
    """Une question (donnée écrite par l'Examinateur à partir d'une leçon non fiable) et la
    réponse de January, chacune dans son encadré."""
    lines = [f"Énoncé : {item.prompt}"]
    if item.code:
        lines.append(f"Code :\n{item.code}")
    lines.append(f"Réponse attendue : {item.expected}")
    lines.append("Grille :\n" + "\n".join(f"- {criterion}" for criterion in item.rubric))
    return (
        f"### {item.ref} ({item.type})\n"
        + untrusted("\n".join(lines), f"question {item.ref}")
        + f"\nRéponse de January à {item.ref} :\n"
        + untrusted(item.answer, "réponse de January")
    )


def _grades_by_ref(found: Grades, items: list[GradingItem]) -> tuple[dict[str, list[Any]], int]:
    """Note de chaque question ouverte (la première donnée pour une référence) ; sans note : 0 et
    `MISSING_FEEDBACK`. Rend aussi le nombre de questions sans note."""
    refs = {item.ref for item in items}
    given: dict[str, GradeDraft] = {}
    for draft in found.items:
        if draft.ref in refs:
            given.setdefault(draft.ref, draft)
    grades: dict[str, list[Any]] = {}
    for item in items:
        grade = given.get(item.ref)
        grades[item.ref] = [grade.score, grade.feedback] if grade else [0.0, MISSING_FEEDBACK]
    return grades, len(refs - given.keys())


def make_grade_open(deps: GraphDeps) -> Node:
    @node_timeout(GRADE_TIMEOUT_S)
    async def grade_open(state: QuizState) -> QuizState:
        attempt = attempt_of(state)
        grades: dict[str, list[Any]] = {ref: [p, ""] for ref, p in attempt.qcm_points.items()}
        if not attempt.open_items:
            return {"grades": grades}
        prompt = render_prompt(
            AGENT,
            mode="grade",
            module_title=attempt.module_title,
            lesson=_lesson(attempt.lesson_markdown),
            items="\n\n".join(_item_prompt(item) for item in attempt.open_items),
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        found = await structured_call(
            model,
            Grades,
            [SystemMessage(prompt), HumanMessage(GRADE_REQUEST)],
            agent=AGENT,
            step="notation",
            intent="je note tes réponses ouvertes",
        )
        open_grades, missing = _grades_by_ref(found, attempt.open_items)
        unknown = sum(1 for grade in found.items if grade.ref not in open_grades)
        logger.info(
            "Réponses notées : session %s, tentative %s, %d ouverte(s), %d sans note, "
            "%d référence(s) inconnue(s)",
            deps.session_id,
            attempt.attempt_id,
            len(attempt.open_items),
            missing,
            unknown,
        )
        return {"grades": grades | open_grades}

    return grade_open
