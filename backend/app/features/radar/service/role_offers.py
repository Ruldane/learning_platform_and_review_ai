"""Compétences demandées dans le dernier relevé exploitable d'un poste et d'une zone."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.features.radar.repository import RadarRunRepository
from app.features.radar.service.entries import is_analyzed
from app.features.radar.service.rules import MAX_RUN


@dataclass(frozen=True)
class OfferSkill:
    name: str
    required: bool


@dataclass(frozen=True)
class RoleOfferSample:
    run_id: str
    role: str
    zone: str
    finished_at: datetime
    offers: tuple[tuple[OfferSkill, ...], ...]


def _needs(raw: list[object]) -> tuple[OfferSkill, ...]:
    skills: list[OfferSkill] = []
    for item in raw:
        if isinstance(item, dict):
            name, required = item.get("name"), item.get("required")
            if isinstance(name, str) and normalize_skill_name(name) and isinstance(required, bool):
                skills.append(OfferSkill(name, required))
    return tuple(skills)


async def latest_role_offers(
    db: AsyncSession, user_id: str, role: str, zone: str
) -> RoleOfferSample | None:
    """Lecture seule du radar. Les liens, textes et scores anciens des offres restent au radar."""
    role_norm, zone_norm = normalize_skill_name(role)[:120], normalize_skill_name(zone)[:120]
    if not role_norm or not zone_norm:
        return None
    run = await RadarRunRepository(db, user_id).latest_done(
        role_norm=role_norm, zone_norm=zone_norm, min_analyzed=1
    )
    if run is None:
        return None
    offers = tuple(_needs(entry["skills"]) for entry in run.postings if is_analyzed(entry))[
        :MAX_RUN
    ]
    return RoleOfferSample(run.id, run.role, run.zone, run.finished_at or run.created_at, offers)
