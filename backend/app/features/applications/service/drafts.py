"""Brouillons de relance (SPEC 6.2, D140) : des gabarits fixes, jamais un appel LLM. Aucun fait
inventé : seuls l'entreprise, le poste, les dates et le prénom du contact y figurent ; une date
absente est omise. Langue de l'offre (`fr` ou `en`) ; la proposition de classer (`close_21`) est
adressée à January, donc toujours en français. Quand la pièce « relances » du kit est prête (et pas
« à vérifier »), son texte remplace le gabarit de 7 jours (`linkedin_7`) et de 14 jours
(`email_14`). Journaux : un brouillon n'est jamais journalisé."""

from datetime import date
from typing import Literal
from urllib.parse import quote

from app.agents.tools.kit_schema import split_followups
from app.db.models.applications import ReminderKind

Language = Literal["fr", "en"]

LINKEDIN_SEARCH = "https://www.linkedin.com/search/results/people/?keywords="
_FR_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
_EN_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_KIT_INDEX: dict[ReminderKind, int] = {"linkedin_7": 0, "email_14": 1}

_FR: dict[ReminderKind, str] = {
    "linkedin_7": (
        "{hello}\n\nJ'ai postulé{applied} au poste de {title} chez {company}. Je me permets de "
        "revenir vers vous pour savoir si ma candidature a bien été reçue et si vous avez besoin "
        "d'un complément d'information de ma part. Ce poste continue de m'intéresser vivement.\n\n"
        "Merci d'avance pour votre retour."
    ),
    "email_14": (
        "Objet : Ma candidature au poste de {title} : relance\n\n{hello}\n\nJe reviens vers vous "
        "au sujet de ma candidature{applied} au poste de {title} chez {company}, restée sans "
        "réponse à ce jour. Ce poste m'intéresse toujours et je reste disponible pour un échange "
        "à votre convenance.\n\nCordialement,"
    ),
    "thanks": (
        "{hello}\n\nMerci pour le temps que vous m'avez accordé lors de notre entretien"
        "{interview} pour le poste de {title} chez {company}. Notre échange a renforcé mon "
        "intérêt pour ce poste. Je reste à votre disposition pour tout complément "
        "d'information.\n\nCordialement,"
    ),
    "news_7": (
        "{hello}\n\nJe me permets de revenir vers vous au sujet de notre entretien{interview} "
        "pour le poste de {title} chez {company}. Auriez-vous des nouvelles sur la suite du "
        "processus ?\n\nMerci d'avance pour votre retour.\n\nCordialement,"
    ),
    "close_21": (
        "{company} ne t'a pas répondu depuis ta candidature{applied} au poste de {title}. "
        "Veux-tu classer cette fiche en « Sans réponse » ?"
    ),
}
_EN: dict[ReminderKind, str] = {
    "linkedin_7": (
        "{hello}\n\nI applied{applied} for the {title} position at {company}. I wanted to follow "
        "up to check that my application reached you, and to see whether you need anything more "
        "from me. I remain very interested in this role.\n\nThank you in advance for your reply."
    ),
    "email_14": (
        "Subject: My application for the {title} position: follow-up\n\n{hello}\n\nI am "
        "following up on my application{applied} for the {title} position at {company}, which "
        "has not received a reply yet. I am still interested in the role and available to talk "
        "at your convenience.\n\nBest regards,"
    ),
    "thanks": (
        "{hello}\n\nThank you for the time you gave me during our interview{interview} for the "
        "{title} position at {company}. Our conversation strengthened my interest in the role. "
        "I remain at your disposal for any further information.\n\nBest regards,"
    ),
    "news_7": (
        "{hello}\n\nI am following up on our interview{interview} for the {title} position at "
        "{company}. Would you have any news on the next steps of the process?\n\n"
        "Thank you in advance for your reply.\n\nBest regards,"
    ),
    "close_21": _FR["close_21"],
}


def _day(day: date, language: Language) -> str:
    if language == "en":
        return f"{_EN_MONTHS[day.month - 1]} {day.day}, {day.year}"
    number = "1er" if day.day == 1 else str(day.day)
    return f"{number} {_FR_MONTHS[day.month - 1]} {day.year}"


def _when(day: date | None, language: Language, kind: Literal["applied", "interview"]) -> str:
    """« le 8 novembre 2026 », « du 14 novembre 2026 », « on November 8, 2026 » ; rien sans date."""
    if day is None:
        return ""
    text = _day(day, language)
    if language == "en":
        return f" on {text}"
    return f" du {text}" if kind == "interview" else f" le {text}"


def _hello(contact_name: str | None, language: Language) -> str:
    first = (contact_name or "").split()
    word = "Hello" if language == "en" else "Bonjour"
    return f"{word} {first[0]}," if first else f"{word},"


def kit_followup(content: str, kind: ReminderKind) -> str | None:
    """Le texte de la pièce « relances » du kit pour cette relance : le courriel de 7 jours est
    avant la première ligne `---`, celui de 14 jours après (`split_followups`, la règle du graphe) ;
    `None` s'il manque."""
    index = _KIT_INDEX.get(kind)
    if index is None:
        return None
    return split_followups(content)[index] or None


def linkedin_search_url(company: str, title: str) -> str:
    """La recherche de personnes LinkedIn « entreprise + poste visé » ; jamais journalisée."""
    return LINKEDIN_SEARCH + quote(f"{company} {title}", safe="")


def draft_for(
    kind: ReminderKind,
    *,
    language: Language,
    company: str,
    title: str,
    contact_name: str | None,
    applied_on: date | None,
    interview_on: date | None,
    kit_followup: str | None,
) -> str:
    """Le brouillon prêt à copier (voir le module)."""
    if kit_followup and kind in _KIT_INDEX:
        return kit_followup
    lang: Language = "fr" if kind == "close_21" else language
    templates = _EN if lang == "en" else _FR
    return templates[kind].format(
        hello=_hello(contact_name, lang),
        company=company,
        title=title,
        applied=_when(applied_on, lang, "applied"),
        interview=_when(interview_on, lang, "interview"),
    )
