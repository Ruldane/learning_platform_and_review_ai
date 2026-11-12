"""Révisions espacées (SPEC F9, D99) : règles pures, sans base ni modèle.

Une fiche réussie passe au palier suivant (1, 3, 7, 16 puis 35 jours) ; une erreur la ramène à
1 jour. Les jours sont ceux de January (fuseau local, `core.clock`) : l'appelant donne `today`.
La file du jour tient en 15 minutes, à 30 secondes la fiche."""

from datetime import date, timedelta

INTERVALS = (1, 3, 7, 16, 35)  # jours avant la prochaine révision, par palier (`step`)
CARD_SECONDS = 30
QUEUE_MINUTES = 15
DAILY_CARDS = QUEUE_MINUTES * 60 // CARD_SECONDS  # 30 fiches par jour au plus
DEMOTE_AFTER = 2  # échecs de fiches consécutifs qui font redescendre un acquis `valide`


def first_due(today: date) -> date:
    """L'échéance d'une fiche neuve (palier 0) : demain."""
    return today + timedelta(days=INTERVALS[0])


def next_review(step: int, ok: bool, today: date) -> tuple[int, date]:
    """`(nouveau palier, nouvelle échéance)` après un avis. Réussite : un palier de plus, borné
    au dernier. Échec : retour au palier 0, demain."""
    new_step = min(step + 1, len(INTERVALS) - 1) if ok else 0
    return new_step, today + timedelta(days=INTERVALS[new_step])


def queue_room(reviewed_today: int) -> int:
    """Combien de fiches tiennent encore dans la file du jour."""
    return max(0, DAILY_CARDS - reviewed_today)
