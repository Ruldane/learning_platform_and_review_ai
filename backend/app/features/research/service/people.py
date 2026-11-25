"""Practitioners spotted by the Scout (SPEC 10.3, D84): a `sources` row of `kind` `person`.

Only public professional information is kept: name (`title`), role (`author`), where they
publish (`summary`, domains separated by "; ") and the address of a page read or of a result
from the session. A person is kept outright (`kept`), without a score.

The fingerprint (`url_hash`) covers the type, the normalized address and the name: a person
never takes the row of the page with the same address, and two practitioners from the same
page (a team) each have their own. Logs: ids only (SPEC 17.2)."""

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
    """Fingerprint of a practitioner: `person`, ALREADY normalized address (`normalize_url`), name
    on one line in lowercase."""
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
    """The practitioner's `sources` row, unique per `(session, url_hash)`: replayed, returns the
    row already written. Raises the `normalize_url` error for an address that is not http(s).
    The commit belongs to the caller."""
    url = normalize_url(person.url)
    key = person_key(url, person.name)
    repo = SourceRepository(db, user_id)
    known = await repo.get_by_url(session_id, key)
    if known is not None:
        return known
    source = await repo.add(_row(session_id, url, key, person))
    logger.info(
        "Practitioner recorded: user %s, session %s, source %s",
        user_id,
        session_id,
        source.id,
    )
    return source


def person_of(source: Source) -> PersonFound:
    """The person as recorded (name, role, address, domains)."""
    where = tuple(part for part in (source.summary or "").split(" ; ") if part)
    return PersonFound(source.title or "", source.author or "", source.url, where)


async def session_people(db: AsyncSession, user_id: str, session_id: str) -> list[Source]:
    """The practitioners of the user's session, in recording order."""
    sources = await SourceRepository(db, user_id).list_for_session(session_id)
    return [source for source in sources if source.kind == "person"]
