"""Périodes et échéances du registre des passages (P13) : règles pures, en heure locale (D98).

Un passage se range par `(user_id, name, period)` ; `period` est le jour local (« 2026-11-16 »),
la semaine ISO locale (« 2026-W47 ») ou tout autre libellé de 16 caractères au plus. Les jours
passés ici sont déjà des jours locaux : le fuseau est appliqué par l'appelant (`local_today`)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.clock import Weekday, local_moment

RADAR_WEEKDAY: Weekday = "monday"
RADAR_TIME = "06:00"
ATS_EVERY_DAYS = 30
MAX_ATTEMPTS = 3


def day_period(day: date) -> str:
    """La période d'un jour local : « 2026-11-16 »."""
    return day.isoformat()


def week_period(day: date) -> str:
    """La période de la semaine ISO (lundi → dimanche) de `day` : « 2026-W47 ». L'année est celle
    de la semaine ISO (le 1er janvier 2027 est en « 2026-W53 »)."""
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def brief_moment(day: date, hhmm: str, zone: ZoneInfo) -> datetime:
    """L'instant UTC où il est `hhmm` le jour local `day` (voir `core.clock.local_moment`)."""
    return local_moment(day, hhmm, zone)


def is_stale(started_at: datetime, now: datetime, minutes: int = 30) -> bool:
    """Vrai si un passage `running` a démarré il y a plus de `minutes` minutes : il est présumé
    mort et peut être repris."""
    return now - started_at > timedelta(minutes=minutes)
