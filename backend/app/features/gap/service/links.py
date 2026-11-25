"""Postings seen from the skills map (SPEC F15, D123): the ready postings whose analysis cites a
skill (detail of a skill) and the skills of a posting (target of the "me against this posting"
comparison). A posting skill is cited under the name of the need or under that of the
reference-list skill the Analyst attached it to (`job_postings.gap`); names are compared
normalized."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.posting_schema import PostingAnalysis
from app.core.skills import normalize_skill_name
from app.db.models.postings import JobPosting
from app.features.gap.repository import GapRepository
from app.features.postings.service.queries import get_posting

POSTINGS_PER_SKILL = 10
LABEL_MAX = 120


@dataclass(frozen=True)
class PostingRef:
    posting_id: str
    title: str


@dataclass(frozen=True)
class PostingSkills:
    label: str  # "Title — Company"
    names: list[str]  # one normalized name per learnable need, in the analysis's order


def _needs(posting: JobPosting, *, learnable_only: bool) -> list[tuple[str, str | None]]:
    """`(need name, attached name or None)` of each need of the analysis, normalized."""
    if posting.analysis is None:
        return []
    analysis = PostingAnalysis.model_validate(posting.analysis)
    matches = (posting.gap or {}).get("matches", [])
    known = {normalize_skill_name(m["need"]): m["known"] for m in matches if m.get("known")}
    found: list[tuple[str, str | None]] = []
    for need in analysis.skills:
        if learnable_only and not need.learnable:
            continue
        norm = normalize_skill_name(need.name)
        found.append((norm, normalize_skill_name(known[norm]) if norm in known else None))
    return found


def _cited(posting: JobPosting) -> set[str]:
    """The names under which the analysis cites its skills: needs and attachments."""
    return {name for pair in _needs(posting, learnable_only=False) for name in pair if name}


def _targets(posting: JobPosting) -> list[str]:
    """One name per learnable need: the attachment if there is one, otherwise the need (the name
    `save_gap` put in the reference list), in the analysis's order, without duplicates."""
    names = (known or need for need, known in _needs(posting, learnable_only=True))
    return list(dict.fromkeys(name for name in names if name))


async def postings_citing(
    db: AsyncSession, user_id: str, names: Sequence[str], limit: int = POSTINGS_PER_SKILL
) -> list[PostingRef]:
    """The ready postings whose analysis cites one of these names (the skill and its synonyms),
    most recent first, `limit` at most."""
    wanted = {norm for norm in map(normalize_skill_name, names) if norm}
    found: list[PostingRef] = []
    for posting in await GapRepository(db, user_id).ready_recent():
        if wanted & _cited(posting):
            found.append(PostingRef(posting.id, posting.title or "Posting"))
            if len(found) == limit:
                break
    return found


async def posting_skills(db: AsyncSession, user_id: str, posting_id: str) -> PostingSkills | None:
    """The learnable skills of one of January's postings; `None` as long as it is not analyzed
    and its gap stored (its needs only enter the reference list at `save_gap`).
    404 `posting_not_found` if it is not hers."""
    posting = await get_posting(db, user_id, posting_id)
    if posting.analysis is None or posting.gap is None or posting.status == "rejected":
        return None
    title = posting.title or "Posting"
    label = f"{title} — {posting.company}" if posting.company else title
    return PostingSkills(label[:LABEL_MAX], _targets(posting))
