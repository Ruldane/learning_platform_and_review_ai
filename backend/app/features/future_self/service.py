"""Projection en lecture seule à partir des données appartenant au compte courant."""

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone, week_start
from app.core.errors import AppError
from app.features.future_self.projection import (
    HISTORY_WEEKS,
    ChapterWork,
    ProjectionInput,
    project,
    skill_key,
)
from app.features.future_self.schemas import FutureSelfOut, FutureSelfQuery, ProjectionSampleOut
from app.features.gap.service.score import GapRow
from app.features.program.service.programs import get_program, list_programs
from app.features.radar.service.role_offers import RoleOfferSample, latest_role_offers
from app.features.radar.service.runs import defaults
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillLevel, SkillsService, higher_level
from app.features.study.service.history import finished_history


@dataclass(frozen=True)
class _ProgramWork:
    program_id: str
    weekly_minutes: int
    chapters: tuple[ChapterWork, ...]


async def _program_work(
    db: AsyncSession, user_id: str, program_id: str | None
) -> _ProgramWork | None:
    if program_id is None:
        programs = await list_programs(db, user_id)
        program_id = next((p.id for p in programs if p.status == "validated"), None)
    if program_id is None:
        return None
    program = await get_program(db, user_id, program_id)
    if program.status != "validated":
        raise AppError(
            "program_not_validated", "Valide d'abord le programme pour le projeter.", 409
        )
    chapters: list[tuple[date, ChapterWork]] = []
    for week in program.weeks:
        for module in week.modules:
            pending = [task for task in module.tasks if task.status == "todo"]
            if not pending or module.skipped:
                continue
            chapter = ChapterWork(
                program.id,
                module.id,
                module.lesson_id if module.lesson_status == "ready" else None,
                module.title,
                sum(task.minutes for task in pending),
                tuple(module.skills),
            )
            chapters.append((max(task.planned_date for task in pending), chapter))
    chapters.sort(key=lambda pair: pair[0])
    return _ProgramWork(
        program.id, program.weekly_minutes, tuple(chapter for _, chapter in chapters)
    )


def alias_map(groups: list[frozenset[str]]) -> dict[str, str]:
    count = Counter(name for group in groups for name in group)
    result: dict[str, str] = {}
    for group in groups:
        # Un synonyme qu'emploient deux compétences ne suffit pas à les confondre.
        unique = {name for name in group if count[name] == 1}
        if unique:
            canonical = min(unique)
            result.update(dict.fromkeys(unique, canonical))
    return result


def _offer_gaps(
    sample: RoleOfferSample | None, levels: dict[str, SkillLevel], aliases: dict[str, str]
) -> tuple[tuple[GapRow, ...], ...]:
    if sample is None:
        return ()
    known: dict[str, SkillLevel] = {}
    for name, level in levels.items():
        key = skill_key(name, aliases)
        old = known.get(key)
        known[key] = higher_level(old, level) if old is not None else level
    offers: list[tuple[GapRow, ...]] = []
    for needs in sample.offers:
        required: dict[str, bool] = {}
        for need in needs:
            key = skill_key(need.name, aliases)
            required[key] = required.get(key, False) or need.required
        offers.append(
            tuple(
                GapRow(skill, needed, known.get(skill), "to_add", None)
                for skill, needed in required.items()
            )
        )
    return tuple(offers)


async def next_chapter_for_skill(
    db: AsyncSession, user_id: str, key: str, aliases: dict[str, str]
) -> ChapterWork | None:
    """Le premier chapitre restant du programme qui vise cette compétence."""
    program = await _program_work(db, user_id, None)
    if program is None:
        return None
    return next(
        (
            chapter
            for chapter in program.chapters
            if any(skill_key(name, aliases) == key for name in chapter.skills)
        ),
        None,
    )


async def forecast(db: AsyncSession, user_id: str, params: FutureSelfQuery) -> FutureSelfOut:
    settings = await SettingsService(db, user_id).get()
    timezone = user_zone(settings.timezone)
    today = local_today(timezone)
    end = week_start(today)
    program = await _program_work(db, user_id, params.program_id)
    default_role, default_zone = await defaults(db, user_id)
    role, zone = params.role or default_role, params.zone or default_zone
    sample = await latest_role_offers(db, user_id, role, zone)
    history = await finished_history(
        db, user_id, zone=timezone, since=end - timedelta(weeks=HISTORY_WEEKS), before=end
    )
    skills = SkillsService(db, user_id)
    aliases = alias_map(await skills.alias_groups())
    observed_offers = _offer_gaps(sample, await skills.known_levels(), aliases)
    result = project(
        ProjectionInput(
            today=today,
            history_started_on=history.first_day,
            studied=history.daily_minutes,
            planned_weekly_minutes=program.weekly_minutes
            if program
            else settings.availability.weekly_budget_minutes,
            alternative_weekly_minutes=params.alternative_weekly_minutes,
            target_percent=params.target_percent,
            offers=observed_offers,
            chapters=program.chapters if program else (),
            skill_aliases=aliases,
        )
    )
    return FutureSelfOut(
        as_of=today,
        role=sample.role if sample else role or None,
        zone=sample.zone if sample else zone,
        program_id=program.program_id if program else None,
        sample=ProjectionSampleOut(
            run_id=sample.run_id, finished_at=sample.finished_at, analyzed=len(sample.offers)
        )
        if sample
        else None,
        **asdict(result),
    )
