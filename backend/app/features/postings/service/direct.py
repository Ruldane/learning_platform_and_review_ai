"""Une offre écrite en direct (phase 10, 10.W) : January ou Claude (par le MCP) donne le texte de
l'offre et son analyse (titre, entreprise, exigences, mots clés, compétences…), l'application les
range comme le fait le port de l'Analyste (`save_analysis`), sans agent, sans session et sans appel
au modèle : l'offre est « prête » aussitôt, avec son élément de mémoire `offre` (indexé) et ses
doublons probables et possibles. L'écart de compétences, lui, se lance comme avant
(`POST /postings/{id}/gap`) : c'est un agent, il n'est pas lancé ici.

Doublons comme `POST /postings` (même lien, ou même texte sans lien : offre existante, 200 ; lien
jamais lu). Une offre en échec ou refusée reçoit l'analyse donnée. Écriture par l'ORM seulement :
l'historique du MCP voit chaque ligne et l'annulation la retire."""

import logging

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.posting_schema import (
    PostingAnalysis,
    enough_text,
    keyword_problems,
    requirement_problems,
)
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.memory.service.direct import author_of, schedule_indexing, write_direct
from app.features.memory.service.upload import normalize_url
from app.features.postings.repository import PostingRepository
from app.features.postings.schemas import (
    TEXT_MAX,
    URL_MAX,
    PostingCreatedOut,
    PostingDirectIn,
    PostingOut,
    PostingPatch,
)
from app.features.postings.service.agent_store import item_title, not_analyzed
from app.features.postings.service.create import (
    Source,
    posting_too_short,
    text_digest,
)
from app.features.postings.service.duplicates import (
    find_duplicates,
    not_found,
    prefetch_scores,
    store_duplicates,
)
from app.features.postings.service.queries import read_posting
from app.features.postings.service.rules import company_key, posting_url_key
from app.features.postings.service.runtime import PostingsRuntime

logger = logging.getLogger(__name__)

TITLE_MAX = 200
MEMORY_REASON = "Saved the text of a posting entered directly."


def posting_analysis_invalid(fields: list[str]) -> AppError:
    """422 : les champs de l'analyse à corriger, jamais leur valeur."""
    return AppError(
        "posting_analysis_invalid",
        "A keyword does not appear in the posting, or a required skill is missing from `skills`.",
        422,
        {"fields": fields},
    )


def _invalid_url() -> AppError:
    return AppError("invalid_url", "Invalid posting link.", 422, {"fields": ["url"]})


def _analysis(data: dict[str, object], text: str) -> PostingAnalysis:
    """L'analyse validée, ses mots clés et ses exigences contrôlés contre le texte (422 sinon)."""
    try:
        analysis = PostingAnalysis.model_validate({**data, "is_job_posting": True})
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
        raise AppError(
            "validation_error",
            "Invalid request. Check the highlighted fields.",
            422,
            {"fields": fields or ["body"]},
        ) from None
    if fields := _problems(analysis, text):
        raise posting_analysis_invalid(fields)
    return analysis


def _source(url: str | None, text: str) -> Source:
    """Le lien normalisé (jamais lu) ou, sans lien, le texte lui-même comme source."""
    if url is None or not url.strip():
        return Source(None, None, text)
    try:
        normalized, key = normalize_url(url), posting_url_key(url)
    except AppError as exc:
        if exc.code in ("invalid_url", "url_forbidden"):
            raise AppError(exc.code, exc.message, 422, {"fields": ["url"]}) from None
        raise
    if len(normalized) > URL_MAX or len(key) > URL_MAX:
        raise _invalid_url()
    return Source(normalized, key, None)


def _apply(posting: JobPosting, analysis: PostingAnalysis) -> None:
    company = (analysis.company or "").strip() or None
    posting.analysis = analysis.model_dump(mode="json")
    posting.title = analysis.title[:TITLE_MAX]
    posting.company = company[:TITLE_MAX] if company else None
    posting.company_norm = (company_key(company) or None) if company else None
    posting.status, posting.failure_reason = "ready", None


async def _existing(
    rt: PostingsRuntime, user_id: str, source: Source, text: str
) -> JobPosting | None:
    async with rt.session_factory() as db:
        repo = PostingRepository(db, user_id)
        if source.url_norm is not None:
            return await repo.by_url_norm(source.url_norm)
        return await repo.by_text_hash(text_digest(text))


def _problems(analysis: PostingAnalysis, text: str) -> list[str]:
    """Les champs de l'analyse que le texte ou la liste `skills` ne tiennent pas."""
    fields = []
    if keyword_problems(analysis, text):
        fields.append("keywords")
    if requirement_problems(analysis):
        fields.append("requirements")
    return fields


async def _memory_and_duplicates(
    db: AsyncSession,
    rt: PostingsRuntime,
    user_id: str,
    posting: JobPosting,
    analysis: PostingAnalysis,
    *,
    scores: dict[str, float],
    is_mcp: bool,
    replaces_title: str | None = None,
) -> None:
    """Dans la transaction de l'offre : son élément de mémoire `offre` (écrit ou mis à jour, pas
    indexé ici : voir `memory.service.direct`), puis ses doublons probables et possibles, rangés
    des deux côtés ; ceux qui ne tiennent plus sont retirés de l'autre côté. `scores` : la recherche
    des offres proches, déjà faite (`_scores`) : aucune attente réseau ici, sous le verrou
    d'écriture."""
    item_id = await write_direct(
        db,
        rt.memory,
        user_id,
        kind="posting",
        title=item_title(analysis),
        text=posting.text,
        tags=("posting",),
        author=author_of(is_mcp),
        reason=MEMORY_REASON,
        replaces=None if replaces_title is None else (replaces_title, posting.text),
    )
    if posting.memory_item_id is None:
        posting.memory_item_id = item_id
    await db.flush()
    hits = await find_duplicates(db, rt.memory, user_id, posting, scores)
    gone = {str(d.get("posting_id")) for d in posting.duplicates if isinstance(d, dict)}
    gone -= {hit.posting_id for hit in hits}
    for other in (await PostingRepository(db, user_id).by_ids(gone)).values():
        other.duplicates = [d for d in other.duplicates if d.get("posting_id") != posting.id]
    await store_duplicates(db, user_id, posting, hits)


async def _scores(
    db: AsyncSession,
    rt: PostingsRuntime,
    user_id: str,
    analysis: PostingAnalysis,
    text: str,
    row: JobPosting | None,
) -> dict[str, float]:
    """La recherche des offres proches (embedding et Qdrant, parfois plusieurs secondes quand Ollama
    est froid), faite **avant la première écriture** : le verrou d'écriture de SQLite n'attend
    jamais le réseau (D66). `row` : l'offre déjà là (reprise ou retouche), `None` pour une neuve."""
    company = (analysis.company or "").strip() or None
    return await prefetch_scores(
        db,
        rt.memory,
        user_id,
        title=analysis.title[:TITLE_MAX],
        company=company[:TITLE_MAX] if company else None,
        text=text,
        own_id=None if row is None else row.id,
        own_item_id=None if row is None else row.memory_item_id,
        distinct_from=[] if row is None else list(row.distinct_from or []),
    )


async def _store(
    rt: PostingsRuntime,
    user_id: str,
    source: Source,
    text: str,
    analysis: PostingAnalysis,
    *,
    is_mcp: bool,
) -> tuple[str, bool] | None:
    """`(id, créée)` : l'offre écrite d'un coup avec son analyse, sa mémoire et ses doublons, en une
    transaction (nouvelle, ou reprise d'une offre dont l'analyse avait échoué) ; `None` si l'offre
    existe déjà et n'a rien à recevoir."""
    async with rt.session_factory() as db:
        found = await _existing(rt, user_id, source, text)
        created = found is None
        if found is not None:
            if found.analysis is not None or found.status not in ("failed", "rejected"):
                return None
            if fields := _problems(analysis, found.text):  # l'offre garde son texte d'origine
                raise posting_analysis_invalid(fields)
            row = await PostingRepository(db, user_id).get_fresh(found.id)
            assert row is not None
            scores = await _scores(db, rt, user_id, analysis, row.text, row)
        else:
            scores = await _scores(db, rt, user_id, analysis, text, None)
            row = JobPosting(
                user_id=user_id,
                url=source.url,
                url_norm=source.url_norm,
                source="url" if source.url_norm else "text",
                text=text,
                text_hash=text_digest(text),
            )
            db.add(row)
        _apply(row, analysis)
        try:
            await db.flush()
            await _memory_and_duplicates(
                db, rt, user_id, row, analysis, scores=scores, is_mcp=is_mcp
            )
            await db.commit()
        except IntegrityError:  # une autre requête vient de l'écrire : on rend la sienne
            await db.rollback()
            return None
        return row.id, created


async def create_direct(
    rt: PostingsRuntime, user_id: str, body: PostingDirectIn, *, is_mcp: bool
) -> PostingCreatedOut:
    """Voir le module. 422 `posting_too_short`, `invalid_url`, `url_forbidden`,
    `posting_analysis_invalid` : jamais l'entrée dans la réponse."""
    text = body.text.strip()
    if not enough_text(text):
        raise posting_too_short()
    analysis = _analysis(body.model_dump(exclude={"text", "url"}), text)
    source = _source(body.url, text)
    async with rt.source_locks.get(user_id, source.key):
        stored = await _store(rt, user_id, source, text, analysis, is_mcp=is_mcp)
        if stored is None:
            existing = await _existing(rt, user_id, source, text)
            if existing is None:
                raise RuntimeError("offre gagnante introuvable après un conflit d'unicité")
            posting_id, created = existing.id, False
        else:
            posting_id, created = stored
            schedule_indexing(rt.memory, user_id)
    logger.info(
        "Offre écrite en direct : utilisateur %s, offre %s, créée %s", user_id, posting_id, created
    )
    async with rt.session_factory() as db:
        posting = await read_posting(db, user_id, posting_id)
    return PostingCreatedOut(posting=posting, created=created, session_id=None)


async def patch_direct(
    rt: PostingsRuntime, user_id: str, posting_id: str, patch: PostingPatch, *, is_mcp: bool
) -> PostingOut:
    """Retouche l'analyse d'une offre analysée (409 `posting_not_analyzed` sinon, 404 si ce n'est
    pas la mienne) : titre, entreprise, niveau, exigences… ; son élément de mémoire et ses
    doublons sont recalculés."""
    changes = patch.model_dump(exclude_none=True)
    async with rt.source_locks.get(user_id, f"posting:{posting_id}"):
        async with rt.session_factory() as db:
            posting = await PostingRepository(db, user_id).get_fresh(posting_id)
            if posting is None:
                raise not_found()
            if posting.analysis is None:
                raise not_analyzed()
            before = item_title(PostingAnalysis.model_validate(posting.analysis))
            analysis = _analysis({**posting.analysis, **changes}, posting.text[:TEXT_MAX])
            scores = await _scores(db, rt, user_id, analysis, posting.text, posting)
            _apply(posting, analysis)
            await _memory_and_duplicates(
                db, rt, user_id, posting, analysis, scores=scores, is_mcp=is_mcp,
                replaces_title=before,
            )  # fmt: skip
            await db.commit()
        schedule_indexing(rt.memory, user_id)
    logger.info("Offre retouchée en direct : utilisateur %s, offre %s", user_id, posting_id)
    async with rt.session_factory() as db:
        return await read_posting(db, user_id, posting_id)
