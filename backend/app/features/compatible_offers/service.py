from collections import Counter
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.db.models.skills import LEVEL_ORDER
from app.features.compatible_offers.schemas import CompatibleOfferOut, CompatibleOfferPlan
from app.features.gap.service import GapRowOut, PlanGapIn
from app.features.gap.service.plan import chosen_skills, no_program
from app.features.gap.service.rows import load_context
from app.features.gap.service.score import GapRow, match_score
from app.features.program.service.replan_gap import latest_validated
from app.features.radar.service.alert_source import AlertSource, alert_source
from app.features.replan.service.launch import start_gap_replan
from app.features.replan.service.runtime import ReplanRuntime
from app.features.skills.service import SkillsService


def _ranked_needs(source: AlertSource, aliases: dict[str, str]) -> dict[str, tuple[str, bool]]:
    needs: dict[str, tuple[str, bool]] = {}
    for need in source.needs:
        normal = normalize_skill_name(need.name)
        key = aliases.get(normal, normal)
        display, required = needs.get(key, (need.name, False))
        needs[key] = (display, required or need.required)
    return needs


async def _rows(db: AsyncSession, user_id: str, source: AlertSource) -> list[GapRow]:
    context = await load_context(db, user_id)
    groups = await SkillsService(db, user_id).alias_groups()
    counts = Counter(alias for group in groups for alias in group)
    aliases: dict[str, str] = {}
    for group in groups:
        unambiguous = {alias for alias in group if counts[alias] == 1}
        if unambiguous:
            aliases.update(dict.fromkeys(unambiguous, min(unambiguous)))

    def row(key: str, name: str, required: bool) -> GapRow:
        candidates = {alias for alias, canonical in aliases.items() if canonical == key} | {key}
        level = next(
            (
                value
                for value in reversed(LEVEL_ORDER)
                if any(context.levels.get(alias) == value for alias in candidates)
            ),
            None,
        )
        week = min(
            (context.weeks[alias] for alias in candidates if alias in context.weeks), default=None
        )
        return GapRow(name, required, level, "in_program" if week is not None else "to_add", week)

    return [
        row(key, name, required) for key, (name, required) in _ranked_needs(source, aliases).items()
    ]


async def get_offer(db: AsyncSession, user_id: str, run_id: str, ref: str) -> CompatibleOfferOut:
    source = await alert_source(db, user_id, run_id, ref)
    rows = await _rows(db, user_id, source)
    return CompatibleOfferOut(
        title=source.title,
        company=source.company,
        url=source.url,
        score=match_score(rows),
        rows=[GapRowOut.model_validate(asdict(row)) for row in rows],
    )


async def plan_offer(
    rt: ReplanRuntime, user_id: str, run_id: str, ref: str, body: PlanGapIn
) -> CompatibleOfferPlan:
    async with rt.session_factory() as db:
        source = await alert_source(db, user_id, run_id, ref)
        gaps = [
            row for row in await _rows(db, user_id, source) if row.level not in {"prouve", "valide"}
        ]
        skills = chosen_skills(gaps, body.skills)
        program_id = body.program_id or await latest_validated(db, user_id)
    if program_id is None:
        raise no_program()
    session_id = await start_gap_replan(rt, user_id, program_id, skills)
    return CompatibleOfferPlan(program_id=program_id, session_id=session_id)
