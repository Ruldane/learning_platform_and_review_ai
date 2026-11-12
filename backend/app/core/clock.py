"""Temps local de January (D98) : le back tourne en UTC, mais ses jours et ses semaines (lundi →
dimanche), sa série, l'échéance de ses fiches et son bilan se comptent dans son fuseau
(`UserSettings.timezone`). Tout calcul de jour ou de semaine passe ici.

Les données des fuseaux viennent du système, sinon du paquet `tzdata`, déclaré en dépendance
pour ne jamais en manquer (image `python:*-slim`, Windows)."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAYS: dict[Weekday, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
DEFAULT_ZONE = "Europe/Paris"


def _load(name: str) -> ZoneInfo | None:
    """Le fuseau IANA `name`, ou `None` s'il est inconnu ou mal formé (chemin, vide…)."""
    if not name or name.startswith("/"):
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None


def is_zone(name: str) -> bool:
    """Vrai si `name` est un fuseau IANA connu."""
    return _load(name) is not None


def user_zone(name: str) -> ZoneInfo:
    """Le fuseau de January ; un nom inconnu donne `Europe/Paris`."""
    return _load(name) or ZoneInfo(DEFAULT_ZONE)


def local_today(zone: ZoneInfo, now: datetime | None = None) -> date:
    """Le jour de January à l'instant `now` (maintenant par défaut ; sans fuseau : UTC)."""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(zone).date()


def week_start(day: date) -> date:
    """Le lundi de la semaine de `day`."""
    return day - timedelta(days=day.weekday())


def local_moment(day: date, hhmm: str, zone: ZoneInfo) -> datetime:
    """L'instant UTC (avec fuseau) où il est `hhmm` (« 18:00 ») le jour `day` chez January.

    Une heure sautée au passage à l'heure d'été est lue avec le décalage d'avant (règle de
    `zoneinfo`, `fold=0`)."""
    hours, minutes = (int(part) for part in hhmm.split(":"))
    return datetime.combine(day, time(hours, minutes), tzinfo=zone).astimezone(UTC)
