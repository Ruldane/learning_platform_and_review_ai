"""Mesures de demandes et de couverture d’exigences dans un relevé."""

from collections.abc import Set

from app.core.skills import normalize_skill_name
from app.features.radar.service.role_offers import OfferSkill

type MarketOffers = tuple[tuple[OfferSkill, ...], ...]


def demand(offers: MarketOffers, name: str) -> float | None:
    if not offers:
        return None
    key = normalize_skill_name(name)
    hits = sum(any(normalize_skill_name(item.name) == key for item in offer) for offer in offers)
    return round(100 * hits / len(offers), 1)


def coverage(offers: MarketOffers, acquired: Set[str]) -> int:
    covered = 0
    for offer in offers:
        required = {normalize_skill_name(item.name) for item in offer if item.required}
        if required and required <= acquired:
            covered += 1
    return covered
