"""Scénario du parcours de bout en bout n° 2 (« revue complète d'un CV », SPEC 18.2) : les réponses
des six agents du CV pour le CV fictif de `scripts/sample_cv.py` (Camille Exemple) et l'offre
fictive de `scripts/sample_posting.py` (Société Fictive), et le web factice de la fiche entreprise.

Chaque réponse reconnaît son appel au dernier marqueur du prompt (la demande de l'agent) : le
nombre d'appels d'un agent peut donc varier (rattachement des compétences seulement si le
référentiel en a, passes de correction du Maquettiste selon le score) sans décaler les suivants.
Les files sont longues ; une réponse qui ne reconnaît pas son appel échoue en nommant l'agent.

Ce que le script fait dire, d'un bout à l'autre (chaque proposition cite des faits du profil) :
- Lecteur ATS `a1` : réécrit « Conçu un assistant… » (aucun fait nouveau : acceptable d'un clic) ;
  `a2` : « 40 % » au lieu de « 30 % » (chiffre absent du profil : « à confirmer ») ; `a3` : une
  ligne qui parle de RAG, mot clé de l'offre absent du profil (il part vers l'écart) ;
- Recruteur `r1` : réécrit « Automatisé… 12 000 factures » (acceptable d'un clic) ;
- aucune objection dans la confrontation."""

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.messages import BaseMessage

from app.agents.nodes.analyst_steps import ANALYZE_REQUEST, MATCH_REQUEST
from app.agents.nodes.archivist_profile import PROFILE_REQUEST
from app.agents.nodes.designer import DRAFT_REQUEST, FIX_REQUEST, SAMPLE_REQUEST
from app.agents.nodes.review_common import PROPOSE_REQUEST
from app.agents.nodes.review_confront import CONFRONT_REQUEST
from app.agents.nodes.scout.company import COMPANY_REQUEST
from app.providers.search.base import SearchResult
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from scripts.sample_cv import CV_FACTS
from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import OutOfOrder, Reply
from tests.support.cv_template import spec as design_spec
from tests.support.cv_templates import sample_reply
from tests.support.gap import analysis_reply
from tests.support.memory import FakeWebReader
from tests.support.profile import experience, profile_reply

F = CV_FACTS
COMPANY = "Société Fictive"
COMPANY_URLS = [f"https://societe-fictive.example.org/{page}" for page in ("a-propos", "equipe")]
FONT = "Liberation Sans"  # la famille choisie pour Helvetica : toujours citable
LONG = 24  # réponses prévues par agent : bien plus que les appels du parcours

# Lignes du CV d'origine reprises par les propositions (faits x1a1, x1a2, x2a1, x2a2).
ACCEPTABLE_ATS = "Conçu et mis en production un assistant interne avec LangGraph pour le support"
TO_CONFIRM = "Réduit de 40 % le temps de traitement des demandes"
GAP_LINE = "Écrit les tests et la documentation des services de données, dont une chaîne RAG"
ACCEPTABLE_RECRUITER = "Automatisé chaque mois le contrôle de 12 000 factures"
GAP_TERM = "RAG"


def dispatch(agent: str, handlers: Mapping[str, Reply]) -> Callable[[Sequence[BaseMessage]], str]:
    """La réponse du gestionnaire dont le marqueur figure le plus bas dans le prompt (la demande
    propre de l'étape vient après le texte système, qui peut en citer d'autres) ; sinon une
    erreur qui nomme l'agent, jamais le prompt."""

    def answer(messages: Sequence[BaseMessage]) -> str:
        prompt = prompt_of(messages)
        found = [(prompt.rfind(marker), marker) for marker in handlers]
        position, marker = max(found)
        if position < 0:
            raise OutOfOrder(f"Réponse scriptée hors d'ordre pour l'agent {agent}.")
        reply = handlers[marker]
        return reply if isinstance(reply, str) else reply(messages)

    return answer


def _queue(agent: str, handlers: Mapping[str, Reply]) -> list[Reply]:
    return [dispatch(agent, handlers) for _ in range(LONG)]


# --- Archiviste, mode `profile` -----------------------------------------------------------------


def profile() -> str:
    """Le profil tiré du CV : deux expériences de deux réalisations (x1a1, x1a2, x2a1, x2a2)."""
    jobs = [
        (F["role_1"], F["company_1"], "2023", "2026", [
            "Conçu un assistant interne avec LangGraph pour le support",
            f"Réduit de {F['metric_1']} le temps de traitement des demandes",
        ]),
        (F["role_2"], F["company_2"], "2020", "2023", [
            f"Automatisé le contrôle de {F['metric_2']} factures par mois",
            "Écrit les tests et la documentation des services de données",
        ]),
    ]  # fmt: skip
    return profile_reply(experiences=[experience(*job) for job in jobs])


# --- Maquettiste (vision) -----------------------------------------------------------------------


def design() -> str:
    """Une description valable : deux colonnes, police du CV (citable dans tous les cas)."""
    fonts = design_spec().fonts.model_dump() | {"body": FONT, "heading": FONT}
    return json.dumps(design_spec().model_dump(mode="json") | {"fonts": fonts}, ensure_ascii=False)


# --- Analyste, Éclaireur, Lecteur ATS, Recruteur ------------------------------------------------


def company_brief() -> str:
    brief = {
        "summary": "Société Fictive édite des assistants conversationnels pour le support.",
        "values": ["Mesurer l'effet de chaque version"],
        "stack": ["LangGraph", "Docker"],
        "tone": "direct",
    }
    return json.dumps(brief, ensure_ascii=False)


def _item(ref: str, target: str, after: str, kind: str, reason: str) -> dict[str, Any]:
    return {
        "ref": ref,
        "section": "experience",
        "action": "rewrite",
        "target": target,
        "after": after,
        "reason": reason,
        "type": kind,
        "fact_ids": [target],
    }


def ats_reading() -> str:
    items = [
        _item("a1", "x1a1", ACCEPTABLE_ATS, "clarity", "Le verbe dit la mise en production."),
        _item("a2", "x1a2", TO_CONFIRM, "impact", "Un résultat plus fort parle à l'offre."),
        _item("a3", "x2a2", GAP_LINE, "keyword", "L'offre demande des chaînes RAG."),
    ]  # fmt: skip
    notes = ["Les intitulés de sections sont usuels : bien lus."]
    return json.dumps({"items": items, "notes": notes}, ensure_ascii=False)


def recruiter_reading() -> str:
    items = [_item("r1", "x2a1", ACCEPTABLE_RECRUITER, "impact", "Le rythme mensuel se lit vite.")]
    strengths = ["Un résultat chiffré par expérience."]
    risks = ["Peu d'éléments sur LangGraph en production."]
    reading = {"items": items, "strengths": strengths, "risks": risks}
    return json.dumps(reading, ensure_ascii=False)


NO_STANCES = json.dumps({"stances": []})
NO_MATCHES = json.dumps({"items": []})  # chaque besoin est alors rattaché par son nom, ou à rien


def _confront() -> dict[str, Reply]:
    return {request: NO_STANCES for request in CONFRONT_REQUEST.values()}


def cv_scripts() -> dict[str, list[Reply]]:
    """Les files de réponses des agents du CV. `scout` est ici le mode `company` : le serveur le
    réunit à l'Éclaireur du Conseil (`merge_scripts`, une file par scénario)."""
    analysis = analysis_reply()
    return {
        "archivist": _queue("archivist", {PROFILE_REQUEST: profile()}),
        "designer": _queue(
            "designer",
            {SAMPLE_REQUEST: sample_reply(), DRAFT_REQUEST: design(), FIX_REQUEST: design()},
        ),
        "analyst": _queue("analyst", {ANALYZE_REQUEST: analysis, MATCH_REQUEST: NO_MATCHES}),
        "scout": _queue("scout", {COMPANY_REQUEST: company_brief()}),
        "ats_reader": _queue("ats_reader", {PROPOSE_REQUEST: ats_reading(), **_confront()}),
        "recruiter": _queue("recruiter", {PROPOSE_REQUEST: recruiter_reading(), **_confront()}),
    }


def script_company_web(reader: FakeWebReader, search: FakeSearch) -> None:
    """La recherche du nom de l'entreprise rend deux pages lisibles (domaine `example.org`)."""
    search.results[COMPANY] = [
        SearchResult(f"Société Fictive, page {n}", url, "extrait", "fake", None)
        for n, url in enumerate(COMPANY_URLS)
    ]
    for url in COMPANY_URLS:
        text = (
            "Société Fictive édite des assistants conversationnels pour les équipes support. "
            "Ses équipes mesurent l'effet de chaque version livrée à ses clients."
        )
        reader.pages[url] = WebDocument(
            url, "Société Fictive", text, None, "2026-09-01", "fr", None
        )
