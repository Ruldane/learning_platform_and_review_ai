"""End of a radar run (P6 to P9, D160): the ranking, the change against the last `done` run of
the same role and zone (normalized), the "absent from your program" alerts, the score of each
posting, the reference list enrichment (without a level, F15), then the `done` status.

Everything is computed by the code, on the **analyzed** postings: `program_alerts` receives the
number of analyzed postings, never that of the postings read. The program's names and the
levels take the reference list's synonyms into account. Idempotent: an already finished run
returns its report without recomputing anything. Logs: ids and numbers only."""

import logging
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.plan_schema import SkillDraft
from app.agents.tools.radar_port import RadarSummary
from app.db.models.daily import RadarRun
from app.db.models.skills import LEVEL_ORDER, SkillLevel
from app.features.program.service.skill_modules import skill_weeks
from app.features.radar.repository import RadarRunRepository
from app.features.radar.service.entries import (
    Entry,
    analysis_failed,
    blocked_domains,
    count,
    is_analyzed,
)
from app.features.radar.service.rules import (
    SkillFreq,
    SkillTrend,
    enrich_names,
    evolution,
    low_sample,
    posting_score,
    program_alerts,
    rank_skills,
)
from app.features.radar.service.runs import radar_run_not_found
from app.features.radar.service.runtime import RadarRuntime
from app.features.skills.service import SkillsService

logger = logging.getLogger(__name__)

ANALYSIS_FAILED = "analysis_failed"
DEFAULT_DOMAIN = "Other"  # what the map shows for a skill without a domain


def summary_of(row: RadarRun) -> RadarSummary:
    """The report of a stored run: readable pages, blocked ones, those that were not postings,
    postings analyzed; reduced sample under 30 readable **postings**."""
    return RadarSummary(
        read_ok=row.read_count,
        blocked=row.blocked_count,
        not_postings=row.not_postings,
        analyzed=row.analyzed,
        low_sample=low_sample(row.read_count - row.not_postings),
        error_code=row.error_code if row.status == "failed" else None,
    )


def _expanded(
    in_program: set[str], levels: dict[str, SkillLevel], groups: list[frozenset[str]]
) -> tuple[set[str], dict[str, SkillLevel]]:
    """The program's names and the levels extended to the synonyms of the same skill: a name
    of the group in the program puts the whole group in the program; the group's best level
    applies to all its names."""
    for group in groups:
        if group & in_program:
            in_program |= group
        known = [levels[name] for name in group if name in levels]
        if known:
            best = max(known, key=LEVEL_ORDER.index)
            levels |= {name: best for name in group}
    return in_program, levels


async def _program_view(
    db: AsyncSession, user_id: str
) -> tuple[set[str], Mapping[str, SkillLevel]]:
    """`(names in the program, levels)`: non-skipped modules of the validated programs
    (`skill_weeks`), known levels (`known_levels`), reference list synonyms included."""
    skills = SkillsService(db, user_id)
    in_program, levels = set(await skill_weeks(db, user_id)), dict(await skills.known_levels())
    return _expanded(in_program, levels, await skills.alias_groups())


def _stored_ranking(row: RadarRun | None) -> list[SkillFreq] | None:
    if row is None:
        return None
    return [
        SkillFreq(
            str(i["skill"]), str(i["norm"]), int(i["count"]), float(i["share"]), int(i["rank"])
        )
        for i in row.ranking
    ]


def _trend_json(item: SkillTrend) -> dict[str, object]:
    return {
        "skill": item.skill,
        "norm": item.norm,
        "count": item.count,
        "share": item.share,
        "rank": item.rank,
        "delta_share": item.delta_share,
        "delta_rank": item.delta_rank,
        "new": item.new,
    }


def _scored(entries: list[Entry], levels: Mapping[str, SkillLevel]) -> list[Entry]:
    """The entries without their text (it only serves extraction), the analyzed postings with
    their match score (levels read by normalized name)."""
    out: list[Entry] = []
    for entry in entries:
        kept = {key: value for key, value in entry.items() if key != "text"}
        if is_analyzed(entry):
            kept["score"] = posting_score(entry["skills"], levels)
        out.append(kept)
    return out


async def finalize_run(rt: RadarRuntime, user_id: str, run_id: str) -> RadarSummary:
    async with rt.run_lock(user_id, run_id), rt.session_factory() as db:
        repo = RadarRunRepository(db, user_id)
        row = await repo.get_fresh(run_id)
        if row is None:
            raise radar_run_not_found()
        if row.status != "running":
            return summary_of(row)
        entries: list[Entry] = list(row.postings)
        counted = count(entries)
        if analysis_failed(entries):  # no posting analyzed: failed, retry possible (D173)
            row.read_count, row.blocked_count = counted.read, counted.blocked
            row.not_postings, row.analyzed = counted.not_postings, 0
            row.blocked_domains = blocked_domains(entries)
            row.status, row.error_code, row.finished_at = "failed", ANALYSIS_FAILED, rt.now()
            await db.commit()
            logger.info("Run without analysis: run %s, %d readable", run_id, counted.read)
            return summary_of(row)
        ranking = rank_skills(entries)
        previous = await repo.latest_done(
            role_norm=row.role_norm,
            zone_norm=row.zone_norm,
            before=row.created_at,
            min_analyzed=1,  # a blind run is not a reference
        )
        in_program, levels = await _program_view(db, user_id)
        alerts = program_alerts(ranking, counted.analyzed, in_program, levels)
        names = [SkillDraft(name=name, domain=DEFAULT_DOMAIN) for name in enrich_names(ranking)]
        await SkillsService(db, user_id).upsert_catalog(names, [])
        row.ranking = [_trend_json(t) for t in evolution(ranking, _stored_ranking(previous))]
        row.alerts = [{"skill": a.skill, "share": a.share, "message": a.message} for a in alerts]
        row.postings = _scored(entries, levels)
        row.read_count, row.blocked_count = counted.read, counted.blocked
        row.not_postings, row.analyzed = counted.not_postings, counted.analyzed
        row.blocked_domains = blocked_domains(entries)
        row.previous_id = previous.id if previous is not None else None
        row.status, row.error_code, row.finished_at = "done", None, rt.now()
        await db.commit()
        summary = summary_of(row)
    logger.info(
        "Run finished: run %s, %d readable, %d blocked, %d analyzed, %d alert(s)",
        run_id,
        summary.read_ok,
        summary.blocked,
        summary.analyzed,
        len(alerts),
    )
    return summary
