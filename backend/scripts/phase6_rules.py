"""Règles du contrôle de la phase 6 (`check_phase6`), en fonctions pures : chacune lit une réponse
de l'API déjà reçue (profil, offre) ou les journaux du back, et lève `CheckFailed` quand une règle
n'est pas tenue. Les messages ne portent que des étapes, des nombres et des noms de champs : jamais
une valeur du profil, du CV ou de l'offre."""

import re
import unicodedata
from typing import Any

from scripts.phase4_rules import CheckFailed
from scripts.sample_cv import CV_FACTS, visible_text
from scripts.sample_posting import POSTING_TEXT

CV_EXPERIENCES = 2  # rôles du CV fictif (`role_1`, `role_2`)
# Ce que les journaux ne contiennent jamais (17.2) : identité, entreprises, texte de l'offre.
POSTING_SENTENCES = (
    "Société Fictive édite des assistants conversationnels pour les équipes support.",
    "Concevoir des agents avec LangGraph et les mettre en production.",
    "Travailler avec le produit pour mesurer l'effet de chaque version.",
)
LOG_FORBIDDEN = (
    "Camille",
    "camille.exemple",
    "00 00 00 00",
    "Société Fictive",
    CV_FACTS["company_1"],
    CV_FACTS["company_2"],
    *POSTING_SENTENCES,
)


def plain(text: str) -> str:
    """Sans accents ni casse ; tout ce qui n'est ni lettre ni chiffre devient une espace."""
    bare = unicodedata.normalize("NFKD", text)
    bare = "".join(c for c in bare if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[^0-9a-z@.+]+", " ", bare).split())


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _named(data: dict[str, Any]) -> list[tuple[str, str]]:
    """`(champ, valeur)` des faits nommés du profil : rôles, entreprises, diplômes, écoles,
    compétences, langues et projets."""
    named: list[tuple[str, str]] = []
    for rank, exp in enumerate(data.get("experiences", [])):
        named += [(f"experiences.{rank}.role", exp["role"])]
        named += [(f"experiences.{rank}.company", exp["company"])]
    for rank, edu in enumerate(data.get("education", [])):
        named += [(f"education.{rank}.degree", edu["degree"])]
        named += [(f"education.{rank}.school", edu["school"])]
    for key in ("skills", "languages", "projects"):
        named += [(f"{key}.{rank}", item["name"]) for rank, item in enumerate(data.get(key, []))]
    return named


def check_profile_facts(step: str, data: dict[str, Any]) -> None:
    """Identité « Camille Exemple », toutes les expériences du CV, aucun fait hors du CV."""
    identity = data.get("identity") or {}
    if identity.get("name") != CV_FACTS["name"]:
        raise CheckFailed(step, "Identité du profil différente de celle du CV fictif.")
    if identity.get("email") and plain(identity["email"]) != plain(CV_FACTS["email"]):
        raise CheckFailed(step, "Champ identity.email différent du CV fictif.")
    if identity.get("phone") and _digits(identity["phone"]) != _digits(CV_FACTS["phone"]):
        raise CheckFailed(step, "Champ identity.phone différent du CV fictif.")
    count = len(data.get("experiences", []))
    if count < CV_EXPERIENCES:
        raise CheckFailed(step, f"{count} expérience(s) : le CV en a {CV_EXPERIENCES}.")
    hay = plain(visible_text())
    outside = [path for path, value in _named(data) if plain(value) not in hay]
    if outside:
        raise CheckFailed(step, f"Faits absents du CV : {', '.join(outside)}.")


def skills_below_declared(step: str, names: list[str], nodes: list[dict[str, Any]]) -> None:
    """Chaque compétence du profil validé a un niveau (au moins `declare`) sur la carte."""
    levels = {plain(node["name"]): node.get("level") for node in nodes}
    missing = [str(rank) for rank, name in enumerate(names) if not levels.get(plain(name))]
    if missing:
        raise CheckFailed(step, f"Compétences sans niveau : skills.{', skills.'.join(missing)}.")


def keywords_in_text(step: str, analysis: dict[str, Any]) -> int:
    """Chaque mot clé gardé figure dans le texte de l'offre ; rend leur nombre."""
    hay = plain(POSTING_TEXT)
    keywords = analysis.get("keywords", [])
    if not keywords:
        raise CheckFailed(step, "Aucun mot clé gardé par l'analyse.")
    absent = [str(rank) for rank, kw in enumerate(keywords) if plain(kw["term"]) not in hay]
    if absent:
        raise CheckFailed(step, f"Mots clés absents du texte : rangs {', '.join(absent)}.")
    return len(keywords)


def check_logs(step: str, logs: str) -> int:
    """Aucune donnée du CV ni de l'offre dans les journaux ; rend le nombre de lignes lues."""
    found = [rank for rank, needle in enumerate(LOG_FORBIDDEN) if needle in logs]
    if found:
        ranks = ", ".join(str(rank) for rank in found)
        raise CheckFailed(step, f"Donnée personnelle dans les journaux (motifs n° {ranks}).")
    return len(logs.splitlines())
