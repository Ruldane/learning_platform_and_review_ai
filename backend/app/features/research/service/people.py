"""Praticiens repérés par l'Éclaireur (SPEC 10.3, D84) : une ligne `sources` de `kind` `person`.

Seules des informations professionnelles publiques sont gardées : nom (`title`), rôle
(`author`), où il publie (`summary`, domaines séparés par « ; ») et l'adresse d'une page lue ou
d'un résultat de la session. Une personne est retenue d'office (`kept`), sans note.

L'empreinte (`url_hash`) couvre le type, l'adresse normalisée et le nom : une personne ne prend
jamais la ligne de la page de même adresse, et deux praticiens d'une même page (une équipe)
ont chacun la leur. Journaux : identifiants seulement (SPEC 17.2)."""

import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.web_port import PersonFound
from app.db.models.research import Source
from app.features.memory.service.upload import normalize_url
from app.features.research.repository import SourceRepository

logger = logging.getLogger(__name__)

_MAX_WHERE = 1000


def person_key(normalized_url: str, name: str) -> str:
    """Empreinte d'un praticien : `person`, adresse DÉJÀ normalisée (`normalize_url`), nom sur
    une ligne en minuscules."""
    folded = " ".join(name.split()).casefold()
    return hashlib.sha256(f"person\n{normalized_url}\n{folded}".encode()).hexdigest()


def _row(session_id: str, url: str, key: str, person: PersonFound) -> Source:
    return Source(
        session_id=session_id,
        kind="person",
        url=url,
        url_hash=key,
        title=" ".join(person.name.split()),
        author=" ".join(person.role.split()),
        lang=None,
        published=None,
        status="ok",
        verdict="kept",
        score=None,
        score_detail=None,
        reason=None,
        summary=" ; ".join(person.where)[:_MAX_WHERE],
    )


async def record_person(
    db: AsyncSession, user_id: str, session_id: str, person: PersonFound
) -> Source:
    """Ligne `sources` du praticien, unique par `(session, url_hash)` : rejouée, rend la ligne
    déjà écrite. Lève l'erreur de `normalize_url` pour une adresse qui n'est pas http(s). Le
    commit appartient à l'appelant."""
    url = normalize_url(person.url)
    key = person_key(url, person.name)
    repo = SourceRepository(db, user_id)
    known = await repo.get_by_url(session_id, key)
    if known is not None:
        return known
    source = await repo.add(_row(session_id, url, key, person))
    logger.info(
        "Praticien enregistré : utilisateur %s, session %s, source %s",
        user_id,
        session_id,
        source.id,
    )
    return source


def person_of(source: Source) -> PersonFound:
    """La personne telle qu'enregistrée (nom, rôle, adresse, domaines)."""
    where = tuple(part for part in (source.summary or "").split(" ; ") if part)
    return PersonFound(source.title or "", source.author or "", source.url, where)


async def session_people(db: AsyncSession, user_id: str, session_id: str) -> list[Source]:
    """Praticiens de la session de l'utilisateur, dans l'ordre d'enregistrement."""
    sources = await SourceRepository(db, user_id).list_for_session(session_id)
    return [source for source in sources if source.kind == "person"]
