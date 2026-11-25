"""Reads the two comparable scans and simulates a time without changing the schedule."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.features.future_self.service import alias_map, next_chapter_for_skill
from app.features.radar.service.role_offers import OfferSkill, RoleOfferSample, latest_role_offers
from app.features.radar.service.runs import defaults
from app.features.skill_market.metrics import MarketOffers, coverage, demand
from app.features.skill_market.schemas import (
    HourSimulation,
    MarketQuery,
    MarketSample,
    SkillMarketOut,
    SkillQuote,
)
from app.features.skills.service import SkillLevel, SkillsService, higher_level

MIN_COMPARABLE_SIZE = 30
HOUR = 60


def _key(name: str, aliases: dict[str, str]) -> str:
    normalized = normalize_skill_name(name)
    return aliases.get(normalized, normalized)


def _canonical(sample: RoleOfferSample | None, aliases: dict[str, str]) -> MarketOffers:
    if sample is None:
        return ()
    return tuple(
        tuple(OfferSkill(_key(item.name, aliases), item.required) for item in offer)
        for offer in sample.offers
    )


def _levels(levels: dict[str, SkillLevel], aliases: dict[str, str]) -> dict[str, SkillLevel]:
    result: dict[str, SkillLevel] = {}
    for name, level in levels.items():
        key = _key(name, aliases)
        current = result.get(key)
        result[key] = higher_level(current, level) if current is not None else level
    return result


def _acquired(level: SkillLevel | None) -> bool:
    return level in {"validated", "proven"}


def _quote(
    key: str, name: str, level: SkillLevel | None, current: MarketOffers, previous: MarketOffers
) -> SkillQuote:
    now = demand(current, key) or 0.0
    before = demand(previous, key)
    return SkillQuote(
        key=key,
        name=name,
        level=level,
        demand_percent=now,
        change_points=None if before is None else round(now - before, 1),
        opportunity=now > 0 and not _acquired(level),
    )


def _names(
    current: RoleOfferSample,
    previous: RoleOfferSample | None,
    levels: dict[str, SkillLevel],
    aliases: dict[str, str],
) -> dict[str, str]:
    names: dict[str, str] = {}
    for sample in (current, previous):
        if sample is None:
            continue
        for offer in sample.offers:
            for need in offer:
                names.setdefault(_key(need.name, aliases), need.name)
    for key in levels:
        names.setdefault(key, key)
    return names


async def _simulate(
    db: AsyncSession,
    user_id: str,
    quote: SkillQuote,
    offers: MarketOffers,
    levels: dict[str, SkillLevel],
    aliases: dict[str, str],
) -> HourSimulation:
    acquired = {key for key, level in levels.items() if _acquired(level)}
    before = coverage(offers, acquired)
    chapter = await next_chapter_for_skill(db, user_id, quote.key, aliases)
    if chapter is None:
        return HourSimulation(
            skill=quote.name,
            chapter=None,
            lesson_id=None,
            remaining_minutes=None,
            progress_percent=None,
            covered_before=before,
            covered_after=None,
        )
    minutes = chapter.minutes
    finishes = minutes <= HOUR
    after = coverage(offers, acquired | {quote.key}) if finishes else before
    return HourSimulation(
        skill=quote.name,
        chapter=chapter.title,
        lesson_id=chapter.lesson_id,
        remaining_minutes=minutes,
        progress_percent=min(100, 100 * HOUR // max(minutes, 1)),
        covered_before=before,
        covered_after=after,
    )


def _sample(value: RoleOfferSample) -> MarketSample:
    return MarketSample(
        run_id=value.run_id, finished_at=value.finished_at, analyzed=len(value.offers)
    )


async def market(db: AsyncSession, user_id: str, query: MarketQuery) -> SkillMarketOut:
    default_role, default_zone = await defaults(db, user_id)
    role = query.role or default_role
    zone = query.zone or default_zone
    current = await latest_role_offers(db, user_id, role, zone)
    if current is None or not current.offers:
        return SkillMarketOut(role=role, zone=zone, current=None, previous=None)
    previous = await latest_role_offers(db, user_id, role, zone, exclude_id=current.run_id)
    skills = SkillsService(db, user_id)
    aliases = alias_map(await skills.alias_groups())
    levels = _levels(await skills.known_levels(), aliases)
    latest, older = _canonical(current, aliases), _canonical(previous, aliases)
    names = _names(current, previous, levels, aliases)
    quotes = tuple(
        sorted(
            (_quote(key, label, levels.get(key), latest, older) for key, label in names.items()),
            key=lambda item: (-item.demand_percent, item.name.casefold()),
        )
    )
    requested = _key(query.skill, aliases) if query.skill else None
    selected = next((quote for quote in quotes if quote.key == requested), None)
    simulation = (
        await _simulate(db, user_id, selected, latest, levels, aliases) if selected else None
    )
    indicative = len(latest) < MIN_COMPARABLE_SIZE or (
        previous is not None and len(older) < MIN_COMPARABLE_SIZE
    )
    return SkillMarketOut(
        role=role,
        zone=zone,
        current=_sample(current),
        previous=_sample(previous) if previous else None,
        quotes=quotes,
        simulation=simulation,
        indicative=indicative,
    )
