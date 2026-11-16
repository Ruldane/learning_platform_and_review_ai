"""Doublons des candidatures (SPEC 6.3, D138) : une offre qui entre dans l'application est
comparée aux fiches existantes, quel que soit l'écran. Fonctions pures : le service (7.2)
construit les `ApplicationView` et l'`Incoming`, la route renvoie les fiches trouvées."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.db.models.applications import ApplicationStatus
from app.features.applications.service.rules import STATUS_LABELS, ApplicationView
from app.features.postings.service.rules import PROBABLE_TITLE, title_similarity

DuplicateLevel = Literal["certain", "probable", "possible"]
HitLevel = DuplicateLevel | Literal["info"]
INFO_DAYS = 30  # une autre fiche chez la même entreprise, dans les 30 derniers jours
_RANK: dict[HitLevel, int] = {"certain": 0, "probable": 1, "possible": 2, "info": 3}
_MONTHS = [
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
]


@dataclass(frozen=True)
class Incoming:
    """L'offre qui entre : son lien normalisé, son entreprise normalisée, son intitulé, son
    identifiant d'offre (s'il existe), ses offres « possibles » (D121), et les identifiants
    (fiches ou offres) que January a déjà confirmés « autre poste » pour elle."""

    url_norm: str | None
    company_norm: str
    title: str
    posting_id: str | None
    possible_posting_ids: frozenset[str]
    distinct_from: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Hit:
    level: HitLevel
    application_id: str


def _reference_day(app: ApplicationView) -> date:
    return app.applied_on or app.created_on


def _is_distinct(incoming: Incoming, app: ApplicationView) -> bool:
    """January a confirmé « autre poste » pour ce couple, dans un sens ou dans l'autre."""
    if incoming.posting_id is not None and incoming.posting_id in app.distinct_from:
        return True
    return app.id in incoming.distinct_from or (
        app.posting_id is not None and app.posting_id in incoming.distinct_from
    )


def _level(incoming: Incoming, app: ApplicationView, today: date) -> HitLevel | None:
    if incoming.url_norm is not None and incoming.url_norm == app.url_norm:
        return "certain"
    if not incoming.company_norm or app.company_norm != incoming.company_norm:
        return None  # une clé vide (nom sans lettre latine) ne désigne aucune entreprise
    if title_similarity(incoming.title, app.title) >= PROBABLE_TITLE:
        return "probable"
    if app.posting_id is not None and app.posting_id in incoming.possible_posting_ids:
        return "possible"
    return "info" if (today - _reference_day(app)).days <= INFO_DAYS else None


def match(incoming: Incoming, apps: Sequence[ApplicationView], today: date) -> list[Hit]:
    """Les fiches qui ressemblent à l'offre entrante, un seul niveau par fiche (le plus fort) :
    même lien : certain ; même entreprise (clé non vide) et intitulé à 85 % : probable ; même
    entreprise et offre « possible » : possible ; même entreprise dans les 30 derniers jours : info.
    La fiche de la même offre (même `posting_id`) n'est jamais un doublon, ni une fiche confirmée
    « autre poste ». Tri : niveau, puis date de candidature (ou de création) décroissante."""
    found: list[tuple[HitLevel, ApplicationView]] = []
    for app in apps:
        if incoming.posting_id is not None and incoming.posting_id == app.posting_id:
            continue
        if _is_distinct(incoming, app):
            continue
        level = _level(incoming, app, today)
        if level is not None:
            found.append((level, app))
    found.sort(key=lambda item: (_RANK[item[0]], -_reference_day(item[1]).toordinal(), item[1].id))
    return [Hit(level, app.id) for level, app in found]


def _day_text(day: date, today: date) -> str:
    """« 3 novembre » (« 1er » pour le premier), l'année ajoutée si elle n'est pas la courante."""
    number = "1er" if day.day == 1 else str(day.day)
    year = f" {day.year}" if day.year != today.year else ""
    return f"{number} {_MONTHS[day.month - 1]}{year}"


def _ago(day: date | None, today: date) -> str:
    if day is None:
        return ""
    days = (today - day).days
    if days <= 0:
        return " aujourd'hui"
    return f" il y a {days} jour{'s' if days > 1 else ''}"


def alert_message(
    level: HitLevel,
    company: str,
    title: str,
    status: ApplicationStatus,
    day: date | None,
    today: date,
) -> str:
    """Le message de l'alerte (SPEC 6.3), en français, sans rien dire de plus que la fiche : la
    date de candidature (ou de création d'une fiche à postuler) et le statut. Un niveau « info »
    reste une simple information."""
    drafted = status == "to_apply"
    if level == "info":
        verb = f"tu as une fiche chez {company}" if drafted else f"tu as postulé chez {company}"
        return f"Pour info : {verb}{_ago(day, today)}, pour le poste {title}."
    when = f" le {_day_text(day, today)}" if day is not None else ""
    label = STATUS_LABELS[status]
    if drafted:
        created = f", créée{when}" if when else ""
        return (
            f"Attention, tu as déjà une fiche chez {company} pour le poste {title}{created}"
            f" (statut : {label})."
        )
    return (
        f"Attention, tu as déjà postulé chez {company} pour le poste {title}{when}"
        f" (statut : {label})."
    )
