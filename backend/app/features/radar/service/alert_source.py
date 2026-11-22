"""Métadonnées d’une offre notée, relues dans le relevé du compte."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.radar_schema import SkillNeedLite
from app.core.errors import AppError
from app.features.radar.repository import RadarRunRepository
from app.features.radar.service.entries import is_analyzed
from app.features.radar.service.rules import HIGH_MATCH


@dataclass(frozen=True)
class AlertSource:
    title: str | None
    company: str | None
    url: str
    needs: tuple[SkillNeedLite, ...]


async def alert_source(db: AsyncSession, user_id: str, run_id: str, ref: str) -> AlertSource:
    run = await RadarRunRepository(db, user_id).get_fresh(run_id)
    if run is not None and run.status == "done":
        for entry in run.postings:
            score = entry.get("score")
            if (
                entry.get("ref") == ref
                and is_analyzed(entry)
                and type(score) is int
                and score >= HIGH_MATCH
            ):
                return AlertSource(
                    entry.get("title"),
                    entry.get("company"),
                    str(entry["url"]),
                    tuple(SkillNeedLite.model_validate(item) for item in entry["skills"]),
                )
    raise AppError("offer_alert_not_found", "Offre du radar introuvable.", 404)
