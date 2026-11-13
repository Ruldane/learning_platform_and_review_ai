"""Réponses scriptées de l'étude (contrôle de fin de phase 5) : le Tuteur d'une session guidée et
l'Examinateur d'un quiz. Chaque agent a UNE file de la même fonction : elle lit la demande dans le
prompt (la dernière phrase du nœud) et rend la sortie structurée qui y répond, sans dépendre de
l'ordre des appels (indices, nouveaux essais, questions reposées).

Tuteur : une question par section (énoncé numéroté, donc différent d'une question à l'autre), des
verdicts `correct`, `partial` puis `wrong` en tournant, trois finales, un bilan. Examinateur : un
quiz de 10 questions sur les 4 types avec 4 fiches ; notation : la première réponse ouverte à 0,5,
les autres à 0 (la note finale reste sous 80 %, le suivi de révision est donc joué)."""

import itertools
import json
import re
from collections.abc import Callable, Sequence

from langchain_core.messages import BaseMessage

from app.agents.nodes.examiner import GRADE_REQUEST, WRITE_REQUEST
from app.agents.nodes.tutor.answers import CHECK_REQUEST, HINT_REQUEST
from app.agents.nodes.tutor.teach import FINAL_REQUEST, REPLY_REQUEST, TEACH_REQUEST
from app.agents.nodes.tutor.wrap import SUMMARY_REQUEST
from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import Reply
from tests.support.quiz import quiz_draft

REPLIES = 80  # appels possibles par agent (un indice ou un essai de plus ne vide pas la file)
VERDICTS = ("correct", "partial", "wrong")
_OPEN_ITEM = re.compile(r"^### (q\d+) \(", re.MULTILINE)

type Answer = Callable[[], str]


def _dispatch(who: str, answers: dict[str, Answer]) -> Reply:
    """Une réponse qui regarde la demande du prompt et rend celle qui lui correspond."""

    def reply(messages: Sequence[BaseMessage]) -> str:
        prompt = prompt_of(messages)
        for request, answer in answers.items():
            if request in prompt:
                return answer()
        raise RuntimeError(f"Modèles scriptés : demande inconnue pour l'agent {who}.")

    return reply


def _tutor() -> Reply:
    sections, verdicts = itertools.count(1), itertools.cycle(VERDICTS)

    def teach() -> str:
        number = next(sections)
        return json.dumps(
            {
                "message": f"Voici le point {number} de la leçon.",
                "question": f"Question {number} : qu'en retiens-tu ?",
                "expected": f"Le point {number}, en une phrase.",
                "mermaid": None,
            }
        )

    finals = [
        {"question": f"Question finale {n} : que retiens-tu ?", "expected": f"Attendu {n}."}
        for n in (1, 2, 3)
    ]
    answers: dict[str, Answer] = {
        TEACH_REQUEST: teach,
        CHECK_REQUEST: lambda: json.dumps({"verdict": next(verdicts), "feedback": "Retour court."}),
        HINT_REQUEST: lambda: json.dumps({"hint": "Pense à ce que la leçon en dit."}),
        FINAL_REQUEST: lambda: json.dumps({"questions": finals}),
        SUMMARY_REQUEST: lambda: json.dumps({"summary": "Bonne séance : les points sont vus."}),
        REPLY_REQUEST: lambda: json.dumps({"message": "Bonne question, voyons cela."}),
    }
    return _dispatch("tutor", answers)


def _grade(messages: Sequence[BaseMessage]) -> str:
    refs = _OPEN_ITEM.findall(prompt_of(messages))
    items = [
        {"ref": ref, "score": 0.5 if n == 0 else 0, "feedback": "Lecture partielle."}
        for n, ref in enumerate(refs)
    ]
    return json.dumps({"items": items})


def _examiner() -> Reply:
    quiz = json.dumps(quiz_draft())

    def reply(messages: Sequence[BaseMessage]) -> str:
        prompt = prompt_of(messages)
        if WRITE_REQUEST in prompt:
            return quiz
        if GRADE_REQUEST in prompt:
            return _grade(messages)
        raise RuntimeError("Modèles scriptés : demande inconnue pour l'agent examiner.")

    return reply


def study_scripts() -> dict[str, list[Reply]]:
    """Les files du Tuteur et de l'Examinateur (la même fonction, `REPLIES` fois)."""
    return {"tutor": [_tutor()] * REPLIES, "examiner": [_examiner()] * REPLIES}
