"""Échéances des relances (SPEC 6.2, D138) : quelles relances une fiche attend, et à quel jour.
Fonctions pures : le service (7.3) compare ce résultat aux relances enregistrées."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.db.models.applications import ReminderKind
from app.features.applications.service.rules import WAITING, ApplicationView

DEFAULT_DELAYS = (7, 14, 21)
MIN_DELAY, MAX_DELAY = 1, 90
POST_INTERVIEW = (1, 7)  # lendemain : remerciement ; 7 jours : demande de nouvelles (fixes, 6.2)
WAITING_KINDS: tuple[ReminderKind, ...] = ("linkedin_7", "email_14", "close_21")
INTERVIEW_KINDS: tuple[ReminderKind, ...] = ("thanks", "news_7")


@dataclass(frozen=True)
class Expected:
    """Une relance attendue : `anchor_on` est la date dont elle découle (candidature ou
    entretien), `due_on` son échéance."""

    kind: ReminderKind
    anchor_on: date
    due_on: date


def validated_delays(raw: Sequence[int]) -> tuple[int, int, int]:
    """Les délais des trois relances d'attente (jours après la candidature) : trois entiers
    strictement croissants de 1 à 90, sinon (7, 14, 21)."""
    ok = (
        len(raw) == len(DEFAULT_DELAYS)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in raw)
        and all(MIN_DELAY <= n <= MAX_DELAY for n in raw)
        and all(a < b for a, b in zip(raw, raw[1:], strict=False))
    )
    return (raw[0], raw[1], raw[2]) if ok else DEFAULT_DELAYS


def expected_reminders(app: ApplicationView, delays: tuple[int, int, int]) -> list[Expected]:
    """Les relances que `app` attend : en attente de réponse (« Postulée » ou « Relancée », avec
    sa date de candidature) : LinkedIn, email et classement aux `delays` ; en « Entretien », avec
    sa date d'entretien : remerciement le lendemain et demande de nouvelles 7 jours après ;
    sinon aucune (une réponse retire les relances d'attente)."""
    if app.status in WAITING and app.applied_on is not None:
        anchor = app.applied_on
        return [
            Expected(kind, anchor, anchor + timedelta(days=days))
            for kind, days in zip(WAITING_KINDS, delays, strict=True)
        ]
    if app.status == "interview" and app.interview_on is not None:
        anchor = app.interview_on
        return [
            Expected(kind, anchor, anchor + timedelta(days=days))
            for kind, days in zip(INTERVIEW_KINDS, POST_INTERVIEW, strict=True)
        ]
    return []
