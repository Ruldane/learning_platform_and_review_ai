"""Gap rows of an offer (F8, D122), recalculated on each read: a level that rises, a validated
program or a CV review changes the table without rewriting anything.

For each skill of the analysis, the stored attachment (`job_postings.gap`) gives the name in the
reference list; the level is that of `user_skills` for this name, otherwise for the name of the
need itself (a need without an attachment enters the reference list at `save_gap`: if it is
acquired later, the row shows it). Then:
- `learnable` false → `out_of_scope`, unless added and accepted in "Offer skills";
- a non-skipped module of a validated program targets the name → `in_program`, with the week of
  its first task;
- otherwise → `to_add`.
Keywords sent to the gap by a CV review (G3) follow, `source="cv_review"`, action `to_add` (or
`in_program`, same rule), unless they are already a row; `match_score` ignores them."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.posting_schema import PostingAnalysis
from app.core.skills import normalize_skill_name
from app.db.models.postings import GapResult, JobPosting
from app.db.models.skills import SkillLevel
from app.features.gap.repository import GapRepository
from app.features.gap.service.score import GapAction, GapRow
from app.features.program.service.skill_modules import skill_coverage
from app.features.skills.service import SkillsService

SKILL_MAX = 120


@dataclass(frozen=True)
class GapContext:
    """What the rows read of January, loaded once for several offers."""

    levels: dict[str, SkillLevel]  # normalized name → level
    weeks: dict[str, int]  # normalized name → week of the validated program
    offer_weeks: dict[str, int]  # coverage of the "Offer skills" modules


async def load_context(db: AsyncSession, user_id: str) -> GapContext:
    levels = await SkillsService(db, user_id).known_levels()
    coverage = await skill_coverage(db, user_id)
    return GapContext(levels, coverage.weeks, coverage.offer_weeks)


def _first[T](values: dict[str, T], names: Sequence[str]) -> T | None:
    for name in names:
        found = values.get(normalize_skill_name(name))
        if found is not None:
            return found
    return None


def posting_rows(analysis: PostingAnalysis, gap: GapResult, ctx: GapContext) -> list[GapRow]:
    """One row per skill of the analysis, in its order."""
    known = {normalize_skill_name(m["need"]): m["known"] for m in gap["matches"]}
    rows: list[GapRow] = []
    for need in analysis.skills:
        match = known.get(normalize_skill_name(need.name))
        names = [name for name in (match, need.name) if name]
        level = _first(ctx.levels, names)
        week = _first(ctx.weeks if need.learnable else ctx.offer_weeks, names)
        action: GapAction = "in_program" if week is not None else "to_add"
        if not need.learnable and week is None:
            action = "out_of_scope"
        rows.append(GapRow(need.name, need.required, level, action, week))
    return rows


def review_rows(
    terms: Sequence[str], rows: Sequence[GapRow], gap: GapResult, ctx: GapContext
) -> list[GapRow]:
    """The keywords from CV reviews that are not already a row (need name or matched reference
    name), once each; `in_program` as soon as a module of a validated program targets them ("Add
    to schedule" accepted, D123), otherwise `to_add`."""
    seen = {normalize_skill_name(row.skill) for row in rows}
    seen |= {normalize_skill_name(m["known"]) for m in gap["matches"] if m["known"]}
    added: list[GapRow] = []
    for term in terms:
        norm = normalize_skill_name(term)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        level, week = ctx.levels.get(norm), ctx.weeks.get(norm)
        action: GapAction = "in_program" if week is not None else "to_add"
        added.append(GapRow(term[:SKILL_MAX], False, level, action, week, "cv_review"))
    return added


def rows_for(posting: JobPosting, ctx: GapContext, terms: Sequence[str]) -> list[GapRow]:
    """The rows of an analysed offer whose attachment is stored; otherwise none."""
    if posting.analysis is None or posting.gap is None:
        return []
    analysis = PostingAnalysis.model_validate(posting.analysis)
    gap: GapResult = {"session_id": posting.gap["session_id"], "matches": posting.gap["matches"]}
    rows = posting_rows(analysis, gap, ctx)
    return rows + review_rows(terms, rows, gap, ctx)


async def gap_rows(db: AsyncSession, user_id: str, posting: JobPosting) -> list[GapRow]:
    """The gap rows of the offer, recalculated (see the module)."""
    if posting.analysis is None or posting.gap is None:
        return []
    ctx = await load_context(db, user_id)
    terms = await GapRepository(db, user_id).review_terms([posting.id])
    return rows_for(posting, ctx, terms.get(posting.id, []))


async def rows_by_posting(
    db: AsyncSession, user_id: str, postings: Sequence[JobPosting]
) -> dict[str, list[GapRow]]:
    """The rows of several offers (list of offers), context loaded once; an offer with no stored
    gap is not listed."""
    ready = [p for p in postings if p.analysis is not None and p.gap is not None]
    if not ready:
        return {}
    ctx = await load_context(db, user_id)
    terms = await GapRepository(db, user_id).review_terms([p.id for p in ready])
    return {p.id: rows_for(p, ctx, terms.get(p.id, [])) for p in ready}
