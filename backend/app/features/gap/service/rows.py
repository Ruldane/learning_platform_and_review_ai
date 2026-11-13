"""Lignes de l'écart d'une offre (F8, D122), recalculées à chaque lecture : un niveau qui monte, un
programme validé ou une revue de CV change le tableau sans rien réécrire.

Pour chaque compétence de l'analyse, le rattachement rangé (`job_postings.gap`) donne le nom du
référentiel ; le niveau est celui de `user_skills` pour ce nom, sinon pour le nom du besoin
lui-même (un besoin sans rattachement entre au référentiel à `save_gap` : s'il est acquis plus
tard, la ligne le montre). Ensuite :
- `learnable` faux → `out_of_scope` ;
- un module non sauté d'un programme validé vise le nom → `in_program`, avec la semaine de sa
  1re tâche ;
- sinon → `to_add`.
Les mots clés envoyés vers l'écart par une revue de CV (G3) suivent, `source="cv_review"`,
action `to_add`, sauf s'ils sont déjà une ligne ; `match_score` les ignore."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.posting_schema import PostingAnalysis
from app.core.skills import normalize_skill_name
from app.db.models.postings import GapResult, JobPosting
from app.db.models.skills import SkillLevel
from app.features.gap.repository import GapRepository
from app.features.gap.service.score import GapAction, GapRow
from app.features.program.service.skill_modules import skill_weeks
from app.features.skills.service import SkillsService

SKILL_MAX = 120


@dataclass(frozen=True)
class GapContext:
    """Ce que les lignes lisent de January, chargé une fois pour plusieurs offres."""

    levels: dict[str, SkillLevel]  # nom normalisé → niveau
    weeks: dict[str, int]  # nom normalisé → semaine du programme validé


async def load_context(db: AsyncSession, user_id: str) -> GapContext:
    levels = await SkillsService(db, user_id).known_levels()
    return GapContext(levels, await skill_weeks(db, user_id))


def _first[T](values: dict[str, T], names: Sequence[str]) -> T | None:
    for name in names:
        found = values.get(normalize_skill_name(name))
        if found is not None:
            return found
    return None


def posting_rows(analysis: PostingAnalysis, gap: GapResult, ctx: GapContext) -> list[GapRow]:
    """Une ligne par compétence de l'analyse, dans son ordre."""
    known = {normalize_skill_name(m["need"]): m["known"] for m in gap["matches"]}
    rows: list[GapRow] = []
    for need in analysis.skills:
        match = known.get(normalize_skill_name(need.name))
        names = [name for name in (match, need.name) if name]
        level = _first(ctx.levels, names)
        week = _first(ctx.weeks, names) if need.learnable else None
        action: GapAction = "in_program" if week is not None else "to_add"
        if not need.learnable:
            action = "out_of_scope"
        rows.append(GapRow(need.name, need.required, level, action, week))
    return rows


def review_rows(
    terms: Sequence[str], rows: Sequence[GapRow], gap: GapResult, ctx: GapContext
) -> list[GapRow]:
    """Les mots clés des revues de CV qui ne sont pas déjà une ligne (nom du besoin ou du
    référentiel rattaché), une fois chacun."""
    seen = {normalize_skill_name(row.skill) for row in rows}
    seen |= {normalize_skill_name(m["known"]) for m in gap["matches"] if m["known"]}
    added: list[GapRow] = []
    for term in terms:
        norm = normalize_skill_name(term)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        level = ctx.levels.get(norm)
        added.append(GapRow(term[:SKILL_MAX], False, level, "to_add", None, "cv_review"))
    return added


def rows_for(posting: JobPosting, ctx: GapContext, terms: Sequence[str]) -> list[GapRow]:
    """Les lignes d'une offre analysée dont le rattachement est rangé ; sinon aucune."""
    if posting.analysis is None or posting.gap is None:
        return []
    analysis = PostingAnalysis.model_validate(posting.analysis)
    gap: GapResult = {"session_id": posting.gap["session_id"], "matches": posting.gap["matches"]}
    rows = posting_rows(analysis, gap, ctx)
    return rows + review_rows(terms, rows, gap, ctx)


async def gap_rows(db: AsyncSession, user_id: str, posting: JobPosting) -> list[GapRow]:
    """Les lignes de l'écart de l'offre, recalculées (voir le module)."""
    if posting.analysis is None or posting.gap is None:
        return []
    ctx = await load_context(db, user_id)
    terms = await GapRepository(db, user_id).review_terms([posting.id])
    return rows_for(posting, ctx, terms.get(posting.id, []))


async def rows_by_posting(
    db: AsyncSession, user_id: str, postings: Sequence[JobPosting]
) -> dict[str, list[GapRow]]:
    """Les lignes de plusieurs offres (liste des offres), contexte chargé une seule fois ; une
    offre sans écart rangé n'y figure pas."""
    ready = [p for p in postings if p.analysis is not None and p.gap is not None]
    if not ready:
        return {}
    ctx = await load_context(db, user_id)
    terms = await GapRepository(db, user_id).review_terms([p.id for p in ready])
    return {p.id: rows_for(p, ctx, terms.get(p.id, [])) for p in ready}
