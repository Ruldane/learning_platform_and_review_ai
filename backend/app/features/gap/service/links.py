"""Les offres vues depuis la carte de compétences (SPEC F15, D123) : les offres prêtes dont
l'analyse cite une compétence (détail d'une compétence) et les compétences d'une offre (cible de
la comparaison « moi face à cette offre »). Une compétence d'offre est citée sous le nom du
besoin ou sous celui du référentiel auquel l'Analyste l'a rattachée (`job_postings.gap`) ; les
noms sont comparés normalisés."""

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
    label: str  # « Titre — Entreprise »
    names: list[str]  # un nom normalisé par besoin apprenable, dans l'ordre de l'analyse


def _needs(posting: JobPosting, *, learnable_only: bool) -> list[tuple[str, str | None]]:
    """`(nom du besoin, nom rattaché ou None)` de chaque besoin de l'analyse, normalisés."""
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
    """Les noms sous lesquels l'analyse cite ses compétences : besoins et rattachements."""
    return {name for pair in _needs(posting, learnable_only=False) for name in pair if name}


def _targets(posting: JobPosting) -> list[str]:
    """Un nom par besoin apprenable : le rattachement s'il existe, sinon le besoin (le nom que
    `save_gap` a mis au référentiel), dans l'ordre de l'analyse, sans doublon."""
    names = (known or need for need, known in _needs(posting, learnable_only=True))
    return list(dict.fromkeys(name for name in names if name))


async def postings_citing(
    db: AsyncSession, user_id: str, names: Sequence[str], limit: int = POSTINGS_PER_SKILL
) -> list[PostingRef]:
    """Les offres prêtes dont l'analyse cite l'un de ces noms (la compétence et ses synonymes),
    les plus récentes d'abord, `limit` au plus."""
    wanted = {norm for norm in map(normalize_skill_name, names) if norm}
    found: list[PostingRef] = []
    for posting in await GapRepository(db, user_id).ready_recent():
        if wanted & _cited(posting):
            found.append(PostingRef(posting.id, posting.title or "Offre"))
            if len(found) == limit:
                break
    return found


async def posting_skills(db: AsyncSession, user_id: str, posting_id: str) -> PostingSkills | None:
    """Les compétences apprenables d'une offre de January ; `None` tant qu'elle n'est pas
    analysée. 404 `posting_not_found` si elle n'est pas à elle."""
    posting = await get_posting(db, user_id, posting_id)
    if posting.analysis is None or posting.status == "rejected":
        return None
    title = posting.title or "Offre"
    label = f"{title} — {posting.company}" if posting.company else title
    return PostingSkills(label[:LABEL_MAX], _targets(posting))
