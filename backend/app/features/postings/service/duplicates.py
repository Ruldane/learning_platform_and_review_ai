"""Doublons d'une offre (SPEC F8, 14.2, D122). Le niveau « certain » (même lien, même texte) est
la réponse 200 de `POST /postings`. Les niveaux « probable » et « possible » demandent l'entreprise
et le titre : ils sont calculés après l'analyse (`save_analysis`, G35) :
- probable : même entreprise (`company_key`) et titres proches (`PROBABLE_TITLE`) ;
- possible : même entreprise, et l'élément de mémoire `offre` de l'autre offre a un fragment
  proche (`POSSIBLE_COSINE`) parmi les 5 premiers résultats de la recherche ;
- « offres distinctes » (`distinct_from`, des deux côtés) les retire ; jamais l'offre elle-même.

Rangés sur les deux offres (`duplicates` : niveau, offre, score), relus à l'affichage : une offre
supprimée disparaît, titre, entreprise et date sont ceux de l'autre offre. Les dates sont rendues
dans le fuseau de January. Journaux : identifiants et nombres seulement."""

import logging
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.gap_port import DuplicateHit, DuplicateLevel
from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.repository import PostingRepository
from app.features.postings.service.rules import (
    POSSIBLE_COSINE,
    PROBABLE_TITLE,
    company_key,
    title_similarity,
)
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

SEARCH_HITS = 5
QUERY_MAX = 500  # `SearchRequest.query`


async def zone_of(db: AsyncSession, user_id: str) -> ZoneInfo:
    return user_zone((await SettingsService(db, user_id).get()).timezone)


def _hit(
    level: DuplicateLevel, other: JobPosting, zone: ZoneInfo, score: float | None
) -> DuplicateHit:
    created = other.created_at.astimezone(zone).isoformat()
    return DuplicateHit(level, other.id, other.title, other.company, created, score)


def _apart(posting: JobPosting, other: JobPosting) -> bool:
    """« Offres distinctes », dit d'un côté ou de l'autre."""
    return other.id in posting.distinct_from or posting.id in other.distinct_from


def search_query(posting: JobPosting) -> str:
    return query_of(posting.title, posting.company, posting.text)


def query_of(title: str | None, company: str | None, text: str) -> str:
    head = " ".join(part for part in (title, company) if part)
    return f"{head}\n{text}".strip()[:QUERY_MAX]


async def _best_scores(
    memory: MemoryRuntime, user_id: str, query: str, own_item_id: str | None, label: str | None
) -> dict[str, float]:
    """`élément de mémoire → meilleur score` des offres proches ; recherche indisponible :
    aucune (le doublon possible n'est qu'un signal)."""
    gateway = AgentMemoryGateway(memory)
    try:
        found = await gateway.search(user_id, query, kinds=["posting"], k=SEARCH_HITS + 1)
    except AppError as exc:
        logger.warning("Doublons possibles non cherchés : offre %s (%s)", label, exc.code)
        return {}
    best: dict[str, float] = {}
    for hit in found.hits:
        if hit.item_id == own_item_id:
            continue
        if hit.item_id in best or len(best) < SEARCH_HITS:
            best[hit.item_id] = max(best.get(hit.item_id, 0.0), hit.score)
    return best


async def prefetch_scores(
    db: AsyncSession,
    memory: MemoryRuntime,
    user_id: str,
    *,
    title: str,
    company: str | None,
    text: str,
    own_id: str | None,
    own_item_id: str | None,
    distinct_from: list[Any],
) -> dict[str, float]:
    """Les scores de recherche dont `find_duplicates` aura besoin pour l'offre décrite, calculés
    **avant toute écriture** : la vectorisation (Ollama) et la recherche (Qdrant) peuvent durer
    plusieurs secondes, et le verrou d'écriture de SQLite ne doit pas les attendre (D66). `{}` sans
    entreprise ou sans autre offre de la même entreprise qui ne soit pas déjà « probable »
    (aucune recherche dans ce cas). `db` ne doit avoir écrit encore aucune ligne."""
    norm = company_key(company) if company else ""
    if not norm:
        return {}
    others = await PostingRepository(db, user_id).same_company(norm, own_id or "")
    rest = [
        other
        for other in others
        if other.memory_item_id
        and other.id not in distinct_from
        and (own_id is None or own_id not in other.distinct_from)
        and title_similarity(title, other.title or "") < PROBABLE_TITLE
    ]
    if not rest:
        return {}
    return await _best_scores(
        memory, user_id, query_of(title, company, text), own_item_id, "écrite"
    )


async def find_duplicates(
    db: AsyncSession,
    memory: MemoryRuntime,
    user_id: str,
    posting: JobPosting,
    scores: dict[str, float] | None = None,
) -> list[DuplicateHit]:
    """Les doublons probables puis possibles de l'offre analysée, les plus anciens d'abord.
    `scores` : ceux que `prefetch_scores` a déjà cherchés (aucune attente réseau ici) ; sinon la
    recherche se fait ici."""
    if not posting.company_norm:
        return []
    same = [
        other
        for other in await PostingRepository(db, user_id).same_company(
            posting.company_norm, posting.id
        )
        if not _apart(posting, other)
    ]
    if not same:
        return []
    zone = await zone_of(db, user_id)
    title = posting.title or ""
    probable = [o for o in same if title_similarity(title, o.title or "") >= PROBABLE_TITLE]
    hits: list[DuplicateHit] = [_hit("probable", other, zone, None) for other in probable]
    rest = [o for o in same if o not in probable and o.memory_item_id]
    if rest and posting.memory_item_id:
        found = (
            scores
            if scores is not None
            else await _best_scores(
                memory, user_id, search_query(posting), posting.memory_item_id, posting.id
            )
        )
        for other in rest:
            score = found.get(other.memory_item_id or "")
            if score is not None and score >= POSSIBLE_COSINE:
                hits.append(_hit("possible", other, zone, round(score, 4)))
    return hits


def _stored(level: str, posting_id: str, score: float | None) -> dict[str, Any]:
    return {"level": level, "posting_id": posting_id, "score": score}


async def store_duplicates(
    db: AsyncSession, user_id: str, posting: JobPosting, hits: list[DuplicateHit]
) -> None:
    """Range les doublons sur l'offre et, réciproquement, sur chaque autre offre (sans doublon de
    ligne). Le commit appartient à l'appelant."""
    posting.duplicates = [_stored(h.level, h.posting_id, h.score) for h in hits]
    others = await PostingRepository(db, user_id).by_ids([h.posting_id for h in hits])
    for hit in hits:
        other = others.get(hit.posting_id)
        if other is None or any(d.get("posting_id") == posting.id for d in other.duplicates):
            continue
        other.duplicates = [*other.duplicates, _stored(hit.level, posting.id, hit.score)]
    await db.flush()


async def shown_duplicates(
    db: AsyncSession, user_id: str, posting: JobPosting, zone: ZoneInfo
) -> list[DuplicateHit]:
    """Les doublons rangés, relus : offres encore là et non déclarées distinctes."""
    stored = [d for d in posting.duplicates if isinstance(d, dict) and d.get("posting_id")]
    others = await PostingRepository(db, user_id).by_ids([str(d["posting_id"]) for d in stored])
    hits: list[DuplicateHit] = []
    for item in stored:
        other = others.get(str(item["posting_id"]))
        level = item.get("level")
        if other is None or _apart(posting, other) or level not in ("probable", "possible"):
            continue
        score = item.get("score")
        hits.append(_hit(level, other, zone, float(score) if score is not None else None))
    return hits


def not_found() -> AppError:
    return AppError("posting_not_found", "Posting not found.", 404)


async def mark_distinct(db: AsyncSession, user_id: str, posting_id: str, other_id: str) -> None:
    """« Offres distinctes » : chacune exclut l'autre et le doublon disparaît des deux côtés.
    Idempotent ; une offre absente (ou d'une autre) : 404. Le commit appartient à l'appelant."""
    found = await PostingRepository(db, user_id).by_ids({posting_id, other_id})
    if posting_id == other_id or len(found) != 2:  # noqa: PLR2004
        raise not_found()
    for one, two in ((posting_id, other_id), (other_id, posting_id)):
        row = found[one]
        if two not in row.distinct_from:
            row.distinct_from = [*row.distinct_from, two]
        row.duplicates = [d for d in row.duplicates if d.get("posting_id") != two]
    await db.flush()
    logger.info(
        "Offres distinctes : utilisateur %s, offres %s et %s", user_id, posting_id, other_id
    )
