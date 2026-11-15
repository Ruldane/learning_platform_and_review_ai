"""Scénario du parcours de bout en bout n° 3 (« une candidature suit son cycle, du doublon à la
relance », SPEC 18.2) : la réponse de l'Assistant de suivi à la phrase de January et le web factice
de l'offre recollée par son lien.

- L'Assistant de suivi (`tracker`, une file) lit « j'ai postulé hier chez Société Fictive pour le
  poste Développeuse IA » : entreprise et poste recopiés de la phrase, statut `applied`, jour de
  « hier » **lu dans le prompt** (la ligne « hier : samedi 14 novembre 2026 (2026-11-14) » que le
  parcours donne au modèle) : aucune horloge truquée, le script suit celle du serveur ;
- l'offre du lien (`POSTING_URL`) a le texte de l'offre fictive de `scripts/sample_posting.py` plus
  une ligne de référence (`PAGE_TEXT`) ; l'offre que le parcours colle d'abord porte la sienne.
  Le parcours n° 2 colle l'offre telle quelle : une offre déjà là de même empreinte de texte
  (collée ou lue d'un lien) serait rendue (200) au lieu d'une offre nouvelle ;
- l'Analyste ne répond ici que pour ces deux offres (la ligne de référence est dans le prompt) :
  même entreprise que le parcours n° 2, **autre intitulé** (`ANALYSIS_TITLE`). Les fiches des deux
  parcours ne se prennent donc pas l'une pour l'autre (doublon « probable ») quel que soit l'ordre
  où ils se jouent ; toute autre offre est lue par l'Analyste du CV (`cv_script.py`), dans la file
  de son scénario (`merge_scripts` : `OutOfOrder` passe la main à l'autre file).
"""

import json
import re
from collections.abc import Sequence

from langchain_core.messages import BaseMessage

from app.agents.nodes.analyst_steps import ANALYZE_REQUEST
from app.agents.nodes.tracker.intake import INTAKE_REQUEST
from app.providers.web.base import WebDocument
from scripts.sample_posting import POSTING_TEXT
from tests.e2e.cv_script import COMPANY, dispatch
from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import OutOfOrder, Reply
from tests.support.gap import analysis_reply
from tests.support.memory import FakeWebReader

SENTENCE = "j'ai postulé hier chez Société Fictive pour le poste Développeuse IA"
TITLE = "Développeuse IA"
POSTING_URL = "https://societe-fictive.example.org/offres/ai-product-engineer"
REFERENCE = "Référence interne : parcours n° 3"  # la ligne qui désigne les offres du parcours
PAGE_TEXT = f"{POSTING_TEXT}\n{REFERENCE} (page du lien).\n"
ANALYSIS_TITLE = "Ingénieure IA appliquée"
LONG = 12  # lectures prévues : une par phrase, plus les nouvelles demandes de `structured_call`

_YESTERDAY = re.compile(r"^- hier : [^\n(]*\((\d{4}-\d{2}-\d{2})\)", re.MULTILINE)


def yesterday(prompt: str) -> str:
    """Le jour de « hier » (AAAA-MM-JJ), tel que le prompt de l'Assistant de suivi le donne."""
    found = _YESTERDAY.search(prompt)
    if found is None:
        raise RuntimeError(
            "Réponse scriptée : le prompt de l'Assistant de suivi n'a pas de « hier »."
        )
    return found.group(1)


def intake_reading(messages: Sequence[BaseMessage]) -> str:
    """La fiche que décrit `SENTENCE` : postulée hier, ni canal, ni contact, ni note."""
    reading = {
        "company": COMPANY,
        "title": TITLE,
        "status": "applied",
        "applied_on": yesterday(prompt_of(messages)),
        "channel": None,
        "contact_name": None,
        "contact_role": None,
        "notes": None,
    }
    return json.dumps(reading, ensure_ascii=False)


def posting_analysis(messages: Sequence[BaseMessage]) -> str:
    """L'analyse d'une offre du parcours (la ligne de référence est dans le prompt), sinon la main
    passe à l'Analyste du CV."""
    if REFERENCE not in prompt_of(messages):
        raise OutOfOrder("Cette offre n'est pas une offre du parcours n° 3.")
    return analysis_reply(title=ANALYSIS_TITLE)


def applications_scripts() -> dict[str, list[Reply]]:
    """Les files du parcours : l'Assistant de suivi (les relances sont des gabarits, sans modèle)
    et l'Analyste des deux offres du parcours."""
    return {
        "tracker": [dispatch("tracker", {INTAKE_REQUEST: intake_reading}) for _ in range(LONG)],
        "analyst": [dispatch("analyst", {ANALYZE_REQUEST: posting_analysis}) for _ in range(LONG)],
    }


def script_posting_web(reader: FakeWebReader) -> None:
    """Le lien de l'offre rend la page de l'offre fictive, lisible en entier."""
    reader.pages[POSTING_URL] = WebDocument(
        POSTING_URL,
        "AI Product Engineer, Société Fictive",
        PAGE_TEXT,
        None,
        "2026-11-01",
        "fr",
        None,
    )
