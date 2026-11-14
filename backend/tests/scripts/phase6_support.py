"""Réponses scriptées du contrôle de la phase 6, partie « capture », contre l'application réelle :
l'Archiviste (profil du CV fictif), le Maquettiste (contenu recopié, description du design) et
l'Analyste (analyse de l'offre fictive, rattachements). Chaque agent a UNE file de la même
fonction : elle lit la demande dans le prompt et rend la sortie qui y répond. Aucun réseau ni
LLM."""

import json
from collections.abc import Callable, Sequence

from langchain_core.messages import BaseMessage

from app.agents.graphs.cv_capture import PROFILE_REQUEST
from app.agents.nodes.analyst_steps import ANALYZE_REQUEST, MATCH_REQUEST
from app.agents.nodes.designer import DRAFT_REQUEST, FIX_REQUEST, SAMPLE_REQUEST
from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import Reply
from tests.features.cv.templates_support import liberation_spec
from tests.support.cv_templates import sample_reply
from tests.support.gap import analysis_reply
from tests.support.profile import profile_reply

REPLIES = 40  # appels possibles par agent (un nouvel essai de plus ne vide pas la file)

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


def _spec() -> str:
    """La description du design, en Liberation Sans (la seule police citable pour Helvetica)."""
    return liberation_spec().model_dump_json()


def capture_scripts() -> dict[str, list[Reply]]:
    """Les files de l'Archiviste, du Maquettiste et de l'Analyste."""
    archivist = _dispatch("archivist", {PROFILE_REQUEST: profile_reply})
    designer = _dispatch(
        "designer",
        {SAMPLE_REQUEST: sample_reply, DRAFT_REQUEST: _spec, FIX_REQUEST: _spec},
    )
    # Aucun rattachement au référentiel : les besoins dont le nom y figure tel quel sont
    # rattachés par le code, les autres restent « à ajouter ».
    no_match = json.dumps({"items": []})
    analyst = _dispatch(
        "analyst", {ANALYZE_REQUEST: analysis_reply, MATCH_REQUEST: lambda: no_match}
    )
    return {
        "archivist": [archivist] * REPLIES,
        "designer": [designer] * REPLIES,
        "analyst": [analyst] * REPLIES,
    }
