"""Relit les rémunérations annuelles brutes en euros du dernier relevé ciblé terminé."""

import re
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.negotiation import SalarySample
from app.agents.tools.posting_schema import normalize_term
from app.core.skills import normalize_skill_name
from app.features.radar.repository import RadarRunRepository
from app.features.radar.service.entries import is_analyzed

_AMOUNT = re.compile(
    r"(?<![\w.,])(?P<value>\d{1,3}(?:[ .,]\d{3})+|\d+(?:[,\.]\d{1,2})?)"
    r"(?P<k>\s*k)?(?![\w.,])",
    re.IGNORECASE,
)
_EURO = r"(?:€|euros?\b|eur\b)"
_CURRENCY = re.compile(rf"\s*{_EURO}", re.IGNORECASE)
_BETWEEN = re.compile(rf"\s*(?:{_EURO}\s*)?(?:[-–—]|à|et|to)\s*", re.IGNORECASE)
_GROSS = re.compile(r"\b(?:brut(?:e?s)?|gross)\b")
_YEARLY = re.compile(r"\b(?:annuel(?:le)?s?|par an|annual|yearly|per year)\b")
_AMBIGUOUS = re.compile(
    r"\b(?:net(?:te?s)?|mensuel(?:le)?s?|par mois|monthly|per month|horaire|hourly|"
    r"par heure|per hour|par jour|per day|daily|tjm|usd|gbp|chf|cad)\b"
)
_ONE_SIDED = re.compile(r"\b(?:jusqu a|a partir de|up to|from|maximum|minimum|au moins)\b")


def _number(match: re.Match[str]) -> Decimal:
    raw = match["value"].replace(" ", "").replace(",", ".")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        raw = raw.replace(".", "")
    return Decimal(raw)


def annual_euro_range(text: str) -> tuple[int, int] | None:
    """Ne convertit aucune période ni devise. Un k€ commun s'applique aux deux bornes."""
    label = normalize_term(text)
    if not _GROSS.search(label) or _AMBIGUOUS.search(label) or "$" in text or "£" in text:
        return None
    if not _YEARLY.search(label) and not re.search(r"/\s*(?:an|year)\b", text, re.IGNORECASE):
        return None
    clean = text.replace("\u00a0", " ").replace("\u202f", " ")
    amounts = list(_AMOUNT.finditer(clean))
    if len(amounts) not in (1, 2) or not _CURRENCY.match(clean, amounts[-1].end()):
        return None
    if len(amounts) == 1 and _ONE_SIDED.search(label):
        return None
    first, last = amounts[0], amounts[-1]
    if first.start() and clean[first.start() - 1] in "-−":
        return None
    if any(match["k"] and re.search(r"[.,]\d{3}", match["value"]) for match in amounts):
        return None
    if len(amounts) == 2 and not _BETWEEN.fullmatch(clean[first.end() : last.start()]):
        return None
    low, high = _number(first), _number(last)
    shared_k = last["k"] and low < 1000 and not _CURRENCY.match(clean, first.end())
    if first["k"] or shared_k:
        low *= 1000
    if last["k"]:
        high *= 1000
    if not 0 < low <= high or low != int(low) or high != int(high):
        return None
    return int(low), int(high)


async def radar_salary(db: AsyncSession, user_id: str, role: str, zone: str) -> SalarySample | None:
    role_norm, zone_norm = normalize_skill_name(role)[:120], normalize_skill_name(zone)[:120]
    if not role_norm or not zone_norm:
        return None
    run = await RadarRunRepository(db, user_id).latest_done(
        role_norm=role_norm, zone_norm=zone_norm, min_analyzed=1
    )
    if run is None:
        return None
    figures = [
        bounds
        for offer in run.postings
        if is_analyzed(offer)
        and isinstance(salary := offer.get("salary"), str)
        and (bounds := annual_euro_range(salary)) is not None
    ]
    if not figures:
        return None
    return SalarySample(
        run_id=run.id,
        role=run.role,
        zone=run.zone,
        minimum_eur=min(low for low, _ in figures),
        maximum_eur=max(high for _, high in figures),
        observations=len(figures),
    )
