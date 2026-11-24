"""Ajout d'une offre (SPEC F8, 14.2, D122) : `POST /postings` avec son lien OU son texte collé.

- Lien : clé `posting_url_key` (paramètres de suivi retirés). Même clé déjà là → l'offre
  existante (200, doublon « certain »). Sinon la page est lue **dans la requête** par la
  recherche web (cache 7 jours, aucune transaction pendant la lecture, D66) ; illisible ou trop
  courte (`enough_text`) → 422 `posting_unreadable` qui demande le texte : aucune offre devinée.
- Texte : trop court → 422 `posting_too_short` ; empreinte sha256 du texte normalisé ; même
  empreinte déjà là → l'offre existante (200).
- Deux envois simultanés de la même source attendent l'un l'autre (verrou par source) ; l'index
  unique (`uq_job_postings_url`, `uq_job_postings_text`) rattrape le reste : la perdante relit la
  gagnante.
- Une offre existante refusée, en échec ou interrompue est relancée plutôt que rendue telle
  quelle.

Une 422 ne recopie jamais l'entrée (`details.fields` seulement). Journaux : identifiants
seulement, jamais le lien, le texte ni l'entreprise (SPEC 17.2)."""

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.agents.tools.posting_schema import enough_text
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.memory.service.upload import normalize_url
from app.features.postings.repository import PostingRepository
from app.features.postings.schemas import TEXT_MAX, URL_MAX, PostingCreatedOut, PostingIn
from app.features.postings.service.launch import launch_new, relaunch
from app.features.postings.service.queries import read_posting
from app.features.postings.service.rules import posting_url_key, route_fragment
from app.features.postings.service.runtime import PostingsRuntime
from app.features.research.service.reading import read

logger = logging.getLogger(__name__)

_SPACES = re.compile(r"\s+")
_URL_ERRORS = ("invalid_url", "url_forbidden")


def posting_source() -> AppError:
    return AppError(
        "posting_source",
        "Provide either the posting link or its text.",
        422,
        {"fields": ["url", "text"]},
    )


def posting_unreadable() -> AppError:
    return AppError(
        "posting_unreadable",
        "This posting could not be read from its link. Paste the posting text instead.",
        422,
        {"fields": ["url"]},
    )


def posting_too_short() -> AppError:
    return AppError(
        "posting_too_short",
        "Posting text is too short. Paste the full posting.",
        422,
        {"fields": ["text"]},
    )


def _url_error(exc: AppError) -> AppError:
    """`invalid_url` ou `url_forbidden`, message fixe, sans l'adresse reçue."""
    return AppError(exc.code, exc.message, 422, {"fields": ["url"]})


def text_digest(text: str) -> str:
    """Empreinte d'un texte d'offre : NFC, blancs réduits à une espace, bords retirés."""
    normalized = _SPACES.sub(" ", unicodedata.normalize("NFC", text)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Source:
    url: str | None  # le lien normalisé (`normalize_url`), lu tel quel
    url_norm: str | None  # la clé d'idempotence (`posting_url_key`)
    text: str | None  # le texte collé ; `None` pour un lien (lu ensuite)

    @property
    def key(self) -> str:
        return f"url:{self.url_norm}" if self.url_norm else f"text:{text_digest(self.text or '')}"


def _given(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def source_of(body: PostingIn) -> Source:
    """Exactement une source, contrôlée (voir le module)."""
    if _given(body.url) == _given(body.text):
        raise posting_source()
    if body.url is not None and body.url.strip():
        try:
            url, key = normalize_url(body.url), posting_url_key(body.url)
        except AppError as exc:
            if exc.code in _URL_ERRORS:
                raise _url_error(exc) from None
            raise
        if len(url) > URL_MAX or len(key) > URL_MAX:
            raise AppError("invalid_url", "The posting link is too long.", 422, {"fields": ["url"]})
        if route_fragment(body.url):  # l'offre est dans l'ancre : la racine du site n'est pas elle
            raise posting_unreadable()
        return Source(url, key, None)
    text = (body.text or "").strip()
    if not enough_text(text):
        raise posting_too_short()
    return Source(None, None, text)


async def _existing(rt: PostingsRuntime, user_id: str, source: Source) -> str | None:
    async with rt.session_factory() as db:
        repo = PostingRepository(db, user_id)
        if source.url_norm is not None:
            found = await repo.by_url_norm(source.url_norm)
        else:
            found = await repo.by_text_hash(text_digest(source.text or ""))
        return None if found is None else found.id


async def _read_page(rt: PostingsRuntime, user_id: str, url: str) -> str:
    """Le texte de la page, lu hors transaction ; illisible ou trop court : 422."""
    try:
        outcome = await read(rt.research, user_id, None, url)
    except AppError as exc:
        if exc.code in _URL_ERRORS:
            raise _url_error(exc) from None
        if exc.status_code == 429:  # noqa: PLR2004  # plafond de la recherche web : tel quel
            raise
        logger.info("Offre illisible : utilisateur %s (%s)", user_id, exc.code)
        raise posting_unreadable() from None
    text = outcome.text.strip()
    if outcome.status != "ok" or not enough_text(text):
        logger.info("Offre illisible ou trop courte : utilisateur %s", user_id)
        raise posting_unreadable()
    return text[:TEXT_MAX]


async def _insert(rt: PostingsRuntime, user_id: str, source: Source, text: str) -> tuple[str, bool]:
    """`(id, créée)` ; l'index unique tranche une course : la perdante relit la gagnante."""
    async with rt.session_factory() as db:
        row = JobPosting(
            user_id=user_id,
            url=source.url,
            url_norm=source.url_norm,
            source="url" if source.url_norm else "text",
            text=text,
            text_hash=text_digest(text),
            status="analyzing",
        )
        db.add(row)
        try:
            await db.commit()
            return row.id, True
        except IntegrityError:
            await db.rollback()
    winner = await _existing(rt, user_id, source)
    if winner is None:
        raise RuntimeError("offre gagnante introuvable après un conflit d'unicité")
    logger.info("Offre ajoutée en double rattrapée : utilisateur %s, offre %s", user_id, winner)
    return winner, False


async def _answer(
    rt: PostingsRuntime, user_id: str, posting_id: str, created: bool, sid: str | None
) -> PostingCreatedOut:
    async with rt.session_factory() as db:
        posting = await read_posting(db, user_id, posting_id)
    return PostingCreatedOut(posting=posting, created=created, session_id=sid)


async def create_posting(rt: PostingsRuntime, user_id: str, body: PostingIn) -> PostingCreatedOut:
    """Voir le module. Rend l'offre, `created` et la session lancée (ou `None`)."""
    source = source_of(body)
    async with rt.source_locks.get(user_id, source.key):
        posting_id = await _existing(rt, user_id, source)
        if posting_id is None:
            text = source.text if source.url is None else await _read_page(rt, user_id, source.url)
            posting_id, created = await _insert(rt, user_id, source, text or "")
            if created:
                logger.info("Offre ajoutée : utilisateur %s, offre %s", user_id, posting_id)
                sid = await launch_new(rt, user_id, posting_id)
                return await _answer(rt, user_id, posting_id, True, sid)
        again = await relaunch(rt, user_id, posting_id, if_needed=True)
        logger.info(
            "Offre déjà ajoutée : utilisateur %s, offre %s, relancée %s",
            user_id,
            posting_id,
            again is not None,
        )
        return await _answer(rt, user_id, posting_id, False, again)
