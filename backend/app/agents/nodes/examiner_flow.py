"""Nœuds de bord du parcours `quiz` (D100) : lire le module ou la tentative, ranger le quiz, son
échec ou les notes, tous par le port `QuizStore`, puis annoncer le résultat.

Chaque écriture du port est idempotente (clé : le quiz, la tentative) : un nœud rejoué après un
arrêt (SPEC 9.4) rend la même chose sans ligne de plus. Le parcours ne pose aucune question : pas
d'`interrupt()`. Journaux : identifiants et nombres seulement, jamais une question ni une
réponse (SPEC 17.2)."""

import logging
from dataclasses import asdict
from typing import Protocol

from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.quiz import QuizState
from app.agents.tools.quiz_port import (
    AttemptToGrade,
    GradedSaved,
    GradingItem,
    ModuleMaterial,
    QuizDraft,
)

AGENT = "examiner"
PASS_PERCENT = 80  # rappelé à January ; la règle elle-même vit dans la feature (`scoring`)
SAVE_TIMEOUT_S = 300  # le port range la note, les fiches, les tâches de suivi et le journal

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: QuizState) -> QuizState: ...


def route_mode(state: QuizState) -> str:
    return "material" if state["mode"] == "generate" else "load_attempt"


def material_of(state: QuizState) -> ModuleMaterial:
    return ModuleMaterial(**state["material"])


def attempt_of(state: QuizState) -> AttemptToGrade:
    data = dict(state["attempt"])
    items = [GradingItem(**item) for item in data.pop("open_items")]
    return AttemptToGrade(open_items=items, **data)


def make_material(deps: GraphDeps) -> Node:
    @node_timeout()
    async def material(state: QuizState) -> QuizState:
        """Le module du quiz et sa leçon (port)."""
        assert state["quiz_id"] is not None  # garanti par `QuizInput`
        found = await deps.ports.quiz.material(deps.user_id, state["quiz_id"])
        return {"material": asdict(found)}

    return material


def make_save_quiz(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save_quiz(state: QuizState) -> QuizState:
        """Questions et fiches rangées (idempotent par quiz), puis annoncées."""
        material = material_of(state)
        assert state["draft"] is not None  # garanti par `route_write`
        draft = QuizDraft.model_validate(state["draft"])
        count = await deps.ports.quiz.save_quiz(
            deps.user_id, deps.session_id, material.quiz_id, draft
        )
        logger.info(
            "Quiz rangé : session %s, quiz %s, %d question(s)",
            deps.session_id,
            material.quiz_id,
            count,
        )
        text = f"Quiz prêt : {count} questions et {len(draft.flashcards)} fiches de révision."
        emit("agent.message", {"message_id": f"{AGENT}-quiz", "text": text}, agent=AGENT)
        artifact = {
            "artifact_id": material.quiz_id,
            "kind": "quiz",
            "title": draft.title,
            "url": f"/etudier/quiz/{material.quiz_id}",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        return {"questions": count, "summary": f"Quiz prêt : « {material.module_title} »."}

    return save_quiz


def make_failed(deps: GraphDeps) -> Node:
    @node_timeout()
    async def failed(state: QuizState) -> QuizState:
        """Quiz en échec, avec sa raison (idempotent). La raison ne cite que des numéros de
        question et des nombres, jamais le contenu écrit par le modèle."""
        material = material_of(state)
        reason = state["failure"]
        await deps.ports.quiz.quiz_failed(deps.user_id, material.quiz_id, reason)
        logger.info("Quiz en échec : session %s, quiz %s", deps.session_id, material.quiz_id)
        text = f"Quiz non écrit : {reason}"
        emit("agent.message", {"message_id": f"{AGENT}-echec", "text": text}, agent=AGENT)
        return {"summary": f"Quiz en échec : « {material.module_title} »."}

    return failed


def make_load_attempt(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load_attempt(state: QuizState) -> QuizState:
        """La tentative à noter : questions ouvertes et réponses, points des QCM, leçon (port)."""
        assert state["attempt_id"] is not None  # garanti par `QuizInput`
        found = await deps.ports.quiz.attempt(deps.user_id, state["attempt_id"])
        return {"attempt": asdict(found)}

    return load_attempt


def make_save_grades(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save_grades(state: QuizState) -> QuizState:
        """Notes rangées par le port (idempotent par tentative : rejoué, il relit la note)."""
        attempt_id = attempt_of(state).attempt_id
        grades = {ref: (float(p), str(text)) for ref, (p, text) in state["grades"].items()}
        saved = await deps.ports.quiz.save_grades(deps.user_id, deps.session_id, attempt_id, grades)
        logger.info(
            "Tentative notée : session %s, tentative %s, %d %%",
            deps.session_id,
            attempt_id,
            saved.score,
        )
        return {"graded": asdict(saved)}

    return save_grades


def graded_text(saved: GradedSaved) -> str:
    """Ce que January lit à la fin de la notation."""
    if saved.passed:
        text = f"Note : {saved.score} %. Acquis validés."
    else:
        text = (
            f"Note : {saved.score} %, il faut {PASS_PERCENT} %. {saved.followup_tasks} tâche(s) "
            "ajoutée(s) au programme, dont un nouvel essai dans 2 jours."
        )
    if saved.cards_created:
        text += f" {saved.cards_created} fiche(s) de révision créée(s) depuis tes erreurs."
    return text


def make_announce(deps: GraphDeps) -> Node:
    @node_timeout()
    async def announce(state: QuizState) -> QuizState:
        """La note annoncée (le détail par question se lit sur la page du quiz)."""
        attempt = attempt_of(state)
        saved = GradedSaved(**state["graded"])
        message = {"message_id": f"{AGENT}-note", "text": graded_text(saved)}
        emit("agent.message", message, agent=AGENT)
        return {"summary": f"Quiz noté : « {attempt.module_title} », {saved.score} %."}

    return announce
