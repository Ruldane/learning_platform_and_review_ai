"""Scénario du parcours de bout en bout n° 1 (« conseil complet », SPEC 18.2) : le web factice
(10 pages) et les réponses de chaque agent, dans l'ordre de ses appels.

Conseil : cadrage de 2 questions ; plan de recherche ; 10 notes (8 retenues, 2 écartées) ;
2 praticiens ; 3 tours × 4 débatteurs (150 mots au plus, citation [1], un autre débatteur nommé,
« Objection : » du Sceptique, January nommée dès qu'elle a écrit) ; 6 tableaux et compte rendu du
Scribe ; 2 propositions. Puis le programme et les 2 leçons (`lesson_script`).

Suppose `debate_rounds` ≥ 2 (3 par défaut) : le Modérateur juge les positions stables au tour 3.
Chaque réponse vérifie qu'elle répond au bon appel (`expect`)."""

import json
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import BaseMessage

from app.providers.search.base import SearchResult
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from tests.e2e.lesson_script import (
    NO_CLAIM,
    expect,
    pick_resources,
    program_plan,
    prompt_of,
    write_lesson,
)
from tests.e2e.scripted_models import Reply
from tests.support.memory import FakeWebReader

QUERY = "ai product engineer"
PAGES = 10
KEPT = 8  # les deux dernières pages sont notées sous 60
URLS = [f"https://site{n}.exemple.org/guide-ai-product" for n in range(PAGES)]
AUTHORS = {0: "Camille Martin", 1: "Léa Dubois"}
DEBATERS = ("strategist", "practitioner", "scout", "skeptic")
ROUNDS = 3
_ADDRESS = re.compile(r"Adresse : (\S+)")
_ROUND = re.compile(r"Tour en cours : (\d+)")
_JANUARY_NOTES = "Messages de January depuis le tour précédent"


def script_web(reader: FakeWebReader, search: FakeSearch) -> None:
    """La requête du plan rend les 10 pages ; chacune est lisible."""
    search.results[QUERY] = [
        SearchResult(f"Guide {n} du métier", url, "extrait", "fake", None)
        for n, url in enumerate(URLS)
    ]
    for n, url in enumerate(URLS):
        text = (
            f"Guide numéro {n} sur le métier d'AI product engineer : prototypes rapides, appels "
            f"d'API, évaluation des réponses et mise en production, section {n}."
        )
        reader.pages[url] = WebDocument(
            url, f"Guide {n} du métier", text, AUTHORS.get(n), "2026-09-01", "fr", None
        )


def _score(messages: Sequence[BaseMessage]) -> str:
    found = _ADDRESS.search(prompt_of(messages))
    kept = found is not None and found.group(1) in URLS[:KEPT]
    parts = (25, 15, 15, 12, 15) if kept else (10, 8, 8, 5, 10)
    names = ("authority", "freshness", "depth", "author", "pedagogy")
    reason = "Guide détaillé et récent." if kept else "Page trop superficielle."
    return json.dumps({**dict(zip(names, parts, strict=True)), "reason": reason, "summary": reason})


_LINES = {
    "strategist": "Je réponds au Praticien : d'abord les appels d'API, puis l'évaluation [1].",
    "practitioner": "Je rejoins le Stratège : un prototype montrable dès la première semaine [1].",
    "scout": "Les sources donnent raison au Sceptique sur la charge de travail [1].",
    "skeptic": "Je réponds à l'Éclaireur : gardons un périmètre réaliste [1].",
}


def _speech(agent: str) -> Reply:
    def speak(messages: Sequence[BaseMessage]) -> str:
        prompt = prompt_of(messages)
        number = _ROUND.search(prompt)
        lines = []
        if _JANUARY_NOTES in prompt:  # message de January à traiter : nommée en premier
            lines.append("January, merci pour ton message : j'en tiens compte dans ce tour.")
        lines.append(f"Tour {number.group(1) if number else '?'}. {_LINES[agent]}")
        if agent == "skeptic":
            lines.append("Objection : dix heures par semaine, c'est serré pour tout couvrir.")
        return "\n".join(lines)

    return expect("À toi de parler.", speak)


def _board(title: str, nodes: list[str]) -> Reply:
    lines = ["flowchart TD"]
    lines += [f'    N{i}["{label}"]' for i, label in enumerate(nodes)]
    lines += [f"    N{i} --> N{i + 1}" for i in range(len(nodes) - 1)]
    return expect("Dessine le tableau.", json.dumps({"title": title, "mermaid": "\n".join(lines)}))


def _proposal(name: str, weeks: int, project: str) -> dict[str, Any]:
    return {
        "name": name,
        "promise": "Construire et évaluer un assistant fondé sur un LLM.",
        "duration_weeks": weeks,
        "weekly_hours": 4,
        "skills": ["API de LLM", "Évaluation de LLM"],
        "final_project": project,
        "tradeoffs": ["Peu de théorie mathématique."],
    }


def _json(marker: str, value: Any) -> Reply:
    return expect(marker, json.dumps(value))


def _moderator() -> list[Reply]:
    order = _json("Fixe l'ordre de parole du tour.", {"order": list(DEBATERS), "intent": "Socle."})
    questions = [
        {"question": "Combien d'heures par semaine peux-tu y consacrer ?"},
        {"question": "As-tu déjà écrit du code Python ?"},
    ]
    review = "Fais le point du tour."
    return [
        _json("Prépare les questions de cadrage.", {"questions": questions}),
        order,
        order,
        _json(review, {"stable": False, "summary": "Les positions bougent encore."}),
        order,
        _json(review, {"stable": True, "summary": "Les positions ne bougent plus."}),
    ]


def _lesson_scout() -> list[Reply]:
    plan = {"queries": [{"text": QUERY, "lang": "fr"}]}
    return [
        _json("Prépare les requêtes de recherche.", plan),
        *[expect("Note cette source.", _score) for _ in range(PAGES)],
        expect("Choisis les ressources.", pick_resources),
    ]


def _scout() -> list[Reply]:
    people = [
        {"name": AUTHORS[0], "role": "AI product engineer", "urls": [URLS[0]]},
        {"name": AUTHORS[1], "role": "Ingénieure en évaluation de LLM", "urls": [URLS[1]]},
    ]
    research = _lesson_scout()[:-1]  # plan et notes, comme pour une leçon
    return [
        *research,
        _json("Repère les praticiens.", {"people": people}),
        *[_speech("scout") for _ in range(ROUNDS)],
        *_lesson_scout(),
        *_lesson_scout(),
    ]


def _scribe() -> list[Reply]:
    minutes = "Le Conseil s'accorde : les API de LLM, puis l'évaluation et un projet final [1]."
    return [
        _board("Carte du domaine", ["AI product engineer", "API de LLM", "Évaluation"]),
        _board("Prérequis", ["Python", "API de LLM", "Évaluation de LLM"]),
        expect("Rédige le compte rendu.", minutes),
        _board("Frise du parcours pratique", ["Semaine 1 : API", "Semaine 2 : évaluation"]),
        _board("Frise du parcours socle", ["Bases", "API", "Évaluation", "Projet"]),
        _board("Comparaison des parcours", ["Pratique : 2 semaines", "Socle : 4 semaines"]),
    ]


def council_scripts() -> dict[str, list[Reply]]:
    """Les files de réponses de chaque agent, du cadrage à la seconde leçon."""
    proposals = [
        _proposal("Parcours pratique", 2, "Un assistant documentaire évalué de bout en bout."),
        _proposal("Parcours socle", 4, "Un assistant de révision avec son banc d'évaluation."),
    ]
    return {
        "moderator": _moderator(),
        "scout": _scout(),
        "strategist": [
            *[_speech("strategist") for _ in range(ROUNDS)],
            _json("Propose les parcours.", {"proposals": proposals}),
            expect("Écris le programme semaine par semaine.", program_plan()),
        ],
        "practitioner": [_speech("practitioner") for _ in range(ROUNDS)],
        "skeptic": [_speech("skeptic") for _ in range(ROUNDS)],
        "scribe": _scribe(),
        "writer": [expect("Écris la leçon.", write_lesson) for _ in range(2)],
        "verifier": [expect("Contrôle les faits de cette leçon.", NO_CLAIM) for _ in range(2)],
    }
