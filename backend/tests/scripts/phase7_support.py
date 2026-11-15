"""Réponses scriptées du contrôle de la phase 7 contre l'application réelle : l'Assistant de suivi
(`tracker` : la phrase de la partie `suivi`, puis les cinq pièces écrites du kit) et l'Éclaireur en
mode `dossier` (`scout`). Chaque agent a UNE file de la même fonction : elle lit la demande dans le
prompt et rend la sortie qui y répond ; sans demande reconnue, `OutOfOrder` (les files se
partagent avec celles du CV : `merge_scripts`). Aucun réseau ni LLM."""

import json
import re
from collections.abc import Callable, Sequence

from langchain_core.messages import BaseMessage

from app.agents.nodes.scout.dossier import DOSSIER_REQUEST
from app.agents.nodes.tracker.intake import INTAKE_REQUEST
from app.agents.nodes.tracker.pieces import SPECS
from tests.agents.graphs.kit_support import (
    answer,
    dossier,
    filler,
    followups,
    form,
    letter,
    linkedin,
)
from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import OutOfOrder, Reply

SENTENCE = re.compile(r"chez (?P<company>.+?) pour le poste (?P<title>[^\n]+)")
YESTERDAY = re.compile(r"hier : [^(\n]*\((\d{4}-\d{2}-\d{2})\)")
LONG = 60  # réponses prévues par agent : bien plus que les appels de plusieurs passages
UNKNOWN_TOOL = "Kubernetes"  # ni le profil ni l'offre ne le disent : la pièce reste « à vérifier »


def intake_reply(messages: Sequence[BaseMessage]) -> str:
    """La fiche de la phrase : entreprise et poste recopiés, postulée hier sur LinkedIn."""
    prompt = prompt_of(messages)
    found = list(SENTENCE.finditer(prompt))
    day = YESTERDAY.search(prompt)
    if not found or day is None:
        raise OutOfOrder("Réponse scriptée hors d'ordre : phrase ou jour introuvables.")
    return json.dumps(
        {
            "company": found[-1].group("company"),
            "title": found[-1].group("title").strip(),
            "status": "applied",
            "applied_on": day.group(1),
            "channel": "linkedin",
            "contact_name": None,
            "contact_role": None,
            "notes": None,
        },
        ensure_ascii=False,
    )


def pitch_with_unknown_tool() -> str:
    """Un pitch de 141 mots qui cite un outil que le profil ne dit pas, à chaque essai."""
    return json.dumps({"text": f"{filler(140)} {UNKNOWN_TOOL}"})


def form_answers() -> str:
    """Une réponse appuyée par un fait du profil, une prétention salariale (vidée par le code)."""
    permit = answer("Avez-vous 3 ans d'expérience ?", "Oui, plusieurs années de métier.", "x1")
    salary = answer("Quelles sont vos prétentions salariales ?", "45 k€ brut annuel.", "x1")
    return form(permit, salary)


def english_letter(words: int = 300) -> str:
    """Une lettre bien dosée mais écrite en anglais (l'offre est en français)."""
    text = "I build reliable solutions with care and I share what I learn every day. "
    return json.dumps({"text": " ".join((text.split() * words)[:words])})


def _dispatch(agent: str, handlers: dict[str, Reply]) -> Callable[[Sequence[BaseMessage]], str]:
    def reply(messages: Sequence[BaseMessage]) -> str:
        prompt = prompt_of(messages)
        position, marker = max((prompt.rfind(marker), marker) for marker in handlers)
        if position < 0:
            raise OutOfOrder(f"Réponse scriptée hors d'ordre pour l'agent {agent}.")
        answer_ = handlers[marker]
        return answer_ if isinstance(answer_, str) else answer_(messages)

    return reply


def phase7_scripts(
    *, pitch: str | None = None, letter_reply: str | None = None
) -> dict[str, list[Reply]]:
    """Les files du `tracker` et du `scout` (dossier), à fusionner avec celles du CV."""
    tracker = _dispatch(
        "tracker",
        {
            INTAKE_REQUEST: intake_reply,
            SPECS["letter"].request: letter_reply or letter(),
            SPECS["linkedin"].request: linkedin(),
            SPECS["followups"].request: followups(),
            SPECS["pitch"].request: pitch or pitch_with_unknown_tool(),
            SPECS["form_answers"].request: form_answers(),
        },
    )
    scout = _dispatch("scout", {DOSSIER_REQUEST: dossier()})
    return {"tracker": [tracker] * LONG, "scout": [scout] * LONG}
