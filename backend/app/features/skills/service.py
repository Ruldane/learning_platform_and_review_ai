"""January's skills (SPEC 4.2, 13.4; D6, D7): the Strategist's reference list (skills,
prerequisites) and levels, which never go down. The commit belongs to the caller."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.core.clock import local_today, user_zone, week_start
from app.core.errors import AppError
from app.core.skills import Evidence, normalize_skill_name, read_evidence
from app.core.skills import evidence as make_evidence
from app.db.models.skills import LEVEL_ORDER, SkillLevel, UserSkill
from app.features.quiz.service.spacing import DEMOTE_AFTER
from app.features.settings.service import SettingsService
from app.features.skills.radar import as_level as _as_level
from app.features.skills.repository import (
    SkillEdgeRepository,
    SkillRepository,
    SkillSnapshotRepository,
    UserSkillRepository,
    users_with_levels,
)
from app.features.skills.schemas import CompareOut, SkillCreate, SkillGraphOut

__all__ = ["SkillLevel", "SkillsService", "higher_level", "write_weekly_snapshots"]

logger = logging.getLogger(__name__)

EVIDENCE_MAX = 20  # evidence kept per skill (the most recent)


async def learning_graph(db: AsyncSession, user_id: str) -> tuple[SkillGraphOut, CompareOut | None]:
    """Map and gaps of the current goal. Reads depend on the Program service."""
    from app.features.skills.compare import compare_with_goal
    from app.features.skills.map import skill_graph

    graph = await skill_graph(db, user_id)
    try:
        target = await compare_with_goal(db, user_id, None)
    except AppError as exc:
        if exc.code != "no_compare_target":
            raise
        target = None
    return graph, target


def higher_level(a: SkillLevel, b: SkillLevel) -> SkillLevel:
    return a if LEVEL_ORDER.index(a) >= LEVEL_ORDER.index(b) else b


def _proof_key(item: Evidence) -> tuple[str, str | None]:
    """Deduplication key: (kind, reference); without a reference, the label decides."""
    return (item["kind"], item["ref_id"] if item["ref_id"] is not None else item["label"])


def _with_proof(raw: Sequence[Any], proof: Evidence) -> list[Evidence]:
    """The re-read evidence, plus `proof` if its (kind, reference) pair is missing (the first
    wins: a replay rewrites nothing), at most `EVIDENCE_MAX` of the most recent."""
    kept = read_evidence(raw)
    if all(_proof_key(item) != _proof_key(proof) for item in kept):
        kept.append(proof)
    return kept[-EVIDENCE_MAX:]


class SkillsService:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._skills = SkillRepository(db, user_id)
        self._edges = SkillEdgeRepository(db, user_id)
        self._levels = UserSkillRepository(db, user_id)

    async def create(self, body: SkillCreate) -> str:
        norm = normalize_skill_name(body.name)
        if not norm:
            raise AppError("invalid_skill_name", "Invalid skill name.", 422)
        created = await self._skills.create(body.name, norm, body.domain, body.synonyms)
        if created is None:
            raise AppError("skill_exists", "This skill already exists.", 409)
        return created

    async def upsert_catalog(
        self, skills: Sequence[SkillDraft], edges: Sequence[EdgeDraft]
    ) -> dict[str, str]:
        """Skills (deduplicated by normalized name) and prerequisite links; returns
        `normalized name → id`. A link with an unknown end, or a loop, is ignored."""
        for skill in skills:
            norm = normalize_skill_name(skill.name)
            if norm:
                await self._skills.ensure(skill.name, norm, skill.domain, list(skill.synonyms))
        names = {normalize_skill_name(s.name) for s in skills} - {""}
        rows = await self._skills.by_norm(names)
        ids = {norm: row.id for norm, row in rows.items()}
        for edge in edges:
            before = ids.get(normalize_skill_name(edge.before))
            after = ids.get(normalize_skill_name(edge.after))
            if before is not None and after is not None and before != after:
                await self._edges.ensure(before, after)
        await self._db.flush()
        return ids

    async def _skill_ids(self, names: Sequence[str]) -> dict[str, tuple[str, str]]:
        """`normalized name → (id, display name)`, skills created as needed (without a domain)."""
        wanted: dict[str, str] = {}
        for name in names:
            norm = normalize_skill_name(name)
            if norm and norm not in wanted:
                wanted[norm] = name.strip()[:120]
        for norm, name in wanted.items():
            await self._skills.ensure(name, norm, None, [])
        rows = await self._skills.by_norm(list(wanted))
        return {norm: (row.id, row.name) for norm, row in rows.items()}

    async def raise_levels(
        self, names: Sequence[str], level: SkillLevel, evidence: Evidence
    ) -> list[tuple[str, SkillLevel]]:
        """Raises each skill to at least `level` (never lower) and records the evidence,
        deduplicated by (kind, reference);
        returns `(name, new level)` of the changed levels only (created ones included)."""
        skills = await self._skill_ids(names)
        ids = [skill_id for skill_id, _ in skills.values()]
        before = await self._levels.for_skills(ids)
        for skill_id in ids:
            if skill_id not in before:  # new: created at the wanted level (a race: nothing)
                await self._levels.ensure(skill_id, level)
        rows = await self._levels.for_skills(ids)
        changed: list[tuple[str, SkillLevel]] = []
        for skill_id, name in skills.values():
            row = rows[skill_id]
            old = before.get(skill_id)
            current = _as_level(old.level) if old is not None else None
            target = higher_level(_as_level(row.level), level)
            row.evidence = list(_with_proof(row.evidence, evidence))
            row.level = target
            if target != current:
                changed.append((name, target))
        await self._db.flush()
        return changed

    async def levels_of(self, names: Sequence[str]) -> list[tuple[str, SkillLevel]]:
        """Current `(display name, level)` of each of these skills that has a level, once per
        normalized name (to reflect the levels in memory)."""
        norms = [norm for norm in dict.fromkeys(map(normalize_skill_name, names)) if norm]
        rows = await self._skills.by_norm(norms)
        levels = await self._levels.for_skills([row.id for row in rows.values()])
        return [
            (rows[norm].name, _as_level(levels[rows[norm].id].level))
            for norm in norms
            if norm in rows and rows[norm].id in levels
        ]

    async def catalog(self) -> list[tuple[str, SkillLevel | None]]:
        """`(display name, level or None)` of each skill of January's reference list, by name
        (posting gap, D122)."""
        levels = await self._levels.by_skill()
        return [
            (skill.name, _as_level(levels[skill.id]) if skill.id in levels else None)
            for skill in await self._skills.list_all()
        ]

    async def alias_groups(self) -> list[frozenset[str]]:
        """The groups of normalized names that designate the same skill of the reference list: its
        name and its synonyms (market radar, P8)."""
        groups: list[frozenset[str]] = []
        for skill in await self._skills.list_all():
            names = {skill.norm_name, *(normalize_skill_name(str(s)) for s in skill.synonyms)}
            groups.append(frozenset(name for name in names if name))
        return groups

    async def known_levels(self) -> dict[str, SkillLevel]:
        """`normalized name → level` of each skill known to January."""
        return {norm: _as_level(level) for norm, level in await self._levels.levels()}

    async def _level_row(self, name: str) -> tuple[str, UserSkill] | None:
        """`(display name, level row)` of the skill, `None` if January does not have it."""
        norm = normalize_skill_name(name)
        rows = await self._skills.by_norm([norm]) if norm else {}
        if norm not in rows:
            return None
        levels = await self._levels.for_skills([rows[norm].id])
        row = levels.get(rows[norm].id)
        return None if row is None else (rows[norm].name, row)

    async def reset_fail_streaks(self, names: Sequence[str]) -> None:
        """A passed quiz resets the card failures of these skills (D101)."""
        for name in dict.fromkeys(names):
            found = await self._level_row(name)
            if found is not None:
                found[1].fail_streak = 0
        await self._db.flush()

    async def record_review(self, skill: str, ok: bool) -> SkillLevel | None:
        """Review of a card of `skill` (F9, D101): success → failures reset to 0; failure → +1.
        A `validated` skill that reaches `DEMOTE_AFTER` consecutive failures drops back to
        `in_progress` (failures reset to 0): the only level decrease allowed; then returns the
        new level, otherwise `None` (skill without a level included)."""
        found = await self._level_row(skill)
        if found is None:
            return None
        row = found[1]
        row.fail_streak = 0 if ok else row.fail_streak + 1
        demoted: SkillLevel | None = None
        if row.level == "validated" and row.fail_streak >= DEMOTE_AFTER:
            row.level, row.fail_streak, demoted = "in_progress", 0, "in_progress"
        await self._db.flush()
        return demoted

    async def skill_id_for(self, name: str) -> str | None:
        """The id of the skill of this (normalized) name, `None` if January's reference list
        does not have it: a skill is never created for a mere piece of evidence."""
        norm = normalize_skill_name(name)
        rows = await self._skills.by_norm([norm]) if norm else {}
        return rows[norm].id if norm in rows else None

    async def existing_name(self, preferred: str, legacy: str) -> str:
        """`legacy` when only a skill of that name exists (stored before the switch to English),
        otherwise `preferred`."""
        if await self.skill_id_for(preferred) is None and await self.skill_id_for(legacy):
            return legacy
        return preferred

    async def add_proof(self, skill_id: str, kind: Literal["ide"], label: str, ref: str) -> None:
        """Evidence of a passed code exercise (`ide`, P20), deduplicated by `ref`. It never
        raises above `in_progress`: a `declared` skill moves there, an `in_progress`,
        `validated` or `proven` skill keeps its level (an exercise validates nothing)."""
        await self._levels.ensure(skill_id, "in_progress")
        row = (await self._levels.for_skills([skill_id])).get(skill_id)
        if row is None:
            return
        proof = make_evidence(kind, ref, label[:200], datetime.now(UTC))
        row.evidence = list(_with_proof(row.evidence, proof))
        if row.level == "declared":
            row.level = "in_progress"
        await self._db.flush()

    async def display_name(self, skill: str) -> str | None:
        """The display name of the skill, `None` if it has no level."""
        found = await self._level_row(skill)
        return None if found is None else found[0]


async def write_weekly_snapshots(
    session_factory: async_sessionmaker[AsyncSession], now: datetime
) -> int:
    """A snapshot of the levels (`skill → level`) per user and per local week (D98): the first
    pass of the week writes it, the following ones change nothing (D106). Called by the
    scheduled task `skill_snapshots`; returns the number of snapshots written."""
    async with session_factory() as db:
        users = await users_with_levels(db)
    written = 0
    for user_id in users:
        async with session_factory() as db:
            zone = user_zone((await SettingsService(db, user_id).get()).timezone)
            levels = await UserSkillRepository(db, user_id).by_skill()
            week = week_start(local_today(zone, now))
            written += await SkillSnapshotRepository(db, user_id).insert_once(week, levels)
            await db.commit()
    level = logging.INFO if written else logging.DEBUG
    logger.log(level, "Skill snapshots: %d user(s), %d written", len(users), written)
    return written
