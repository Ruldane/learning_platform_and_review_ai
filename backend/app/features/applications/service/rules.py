"""Règles pures des candidatures (SPEC 6.1, 6.4, D138) : l'ordre des statuts, ce qu'un changement
de statut pose comme dates, les indicateurs. Aucune base de données : le service construit des
`ApplicationView` (7.2) et les passe ici."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import get_args

from app.db.models.applications import ApplicationStatus

# Kanban column order (SPEC 6.1), from To apply to Withdrawn.
STATUS_ORDER: tuple[ApplicationStatus, ...] = get_args(ApplicationStatus)
STATUS_LABELS: dict[ApplicationStatus, str] = {
    "to_apply": "To apply",
    "applied": "Applied",
    "followed_up": "Followed up",
    "interview": "Interview",
    "offer": "Offer",
    "rejected": "Rejected",
    "no_answer": "No answer",
    "withdrawn": "Withdrawn",
}
ANSWERED: frozenset[ApplicationStatus] = frozenset({"interview", "offer", "rejected"})
WAITING: frozenset[ApplicationStatus] = frozenset({"applied", "followed_up"})


@dataclass(frozen=True)
class ApplicationView:
    """Ce que les règles lisent d'une fiche : jamais la ligne de la base."""

    id: str
    status: ApplicationStatus
    company_norm: str
    title: str
    url_norm: str | None
    posting_id: str | None
    applied_on: date | None
    interview_on: date | None
    answered_on: date | None
    created_on: date
    distinct_from: frozenset[str] = frozenset()


@dataclass(frozen=True)
class StatusEffects:
    """Les dates qu'un changement de statut pose (`None` : le champ ne change pas)."""

    applied_on: date | None = None
    interview_on: date | None = None
    answered_on: date | None = None

    def fields(self) -> dict[str, date]:
        """Les champs posés, nom de colonne → date."""
        values = {
            "applied_on": self.applied_on,
            "interview_on": self.interview_on,
            "answered_on": self.answered_on,
        }
        return {name: value for name, value in values.items() if value is not None}


@dataclass(frozen=True)
class Stats:
    by_status: dict[ApplicationStatus, int]
    response_rate: float | None  # répondues / postulées, `None` sans candidature postulée
    mean_response_days: float | None  # `None` sans réponse
    due: int  # relances dues


def on_status(app: ApplicationView, new: ApplicationStatus, day: date) -> StatusEffects:
    """Les dates posées quand `app` passe à `new` le jour `day` : la date de candidature à
    « Postulée » (une fois), la date d'entretien à « Entretien » (si January n'en a pas donné
    une), la date de première réponse à la première entrée dans `ANSWERED` (elle ne bouge plus).
    Tout statut est permis, y compris le retour à « À postuler » (January corrige) : aucune date
    n'est alors effacée."""
    return StatusEffects(
        applied_on=day if new == "applied" and app.applied_on is None else None,
        interview_on=day if new == "interview" and app.interview_on is None else None,
        answered_on=day if new in ANSWERED and app.answered_on is None else None,
    )


def stats(apps: Sequence[ApplicationView], due_reminders: int) -> Stats:
    """Les indicateurs (SPEC 6.4) : fiches par statut (les huit, zéro compris), taux de réponse
    (répondues / postulées, une fiche est postulée quand `applied_on` est renseignée), délai
    moyen de réponse en jours (arrondi à 0,1) et relances dues."""
    by_status: dict[ApplicationStatus, int] = dict.fromkeys(STATUS_ORDER, 0)
    for app in apps:
        by_status[app.status] += 1
    delays = [
        (app.answered_on - app.applied_on).days
        for app in apps
        if app.applied_on is not None and app.answered_on is not None
    ]
    applied = sum(1 for app in apps if app.applied_on is not None)
    return Stats(
        by_status=by_status,
        response_rate=len(delays) / applied if applied else None,
        mean_response_days=round(sum(delays) / len(delays), 1) if delays else None,
        due=due_reminders,
    )
