"""The Scout spots practitioners (SPEC 10.3, D84): real people who publish on the topic, 10 at
most, with their name, their role and where they publish. Public professional information
only.

The model only sees the selected pages (title, author, address, wrapped as untrusted). A person
is kept only if at least one of their addresses is a page read or a result of the session: the
recorded address is then the session's, never the one the model wrote. A person without a known
address is discarded: never invented."""

import logging
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.nodes.scout.models import AGENT, one_line, page_title
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.prose import Prose
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState
from app.agents.tools.web_port import PersonFound
from app.core.errors import AppError

MAX_PEOPLE = 10
INVALID_OUTPUT_CODE = "structured_output_invalid"

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CouncilState) -> CouncilState: ...


class PersonModel(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: Prose = Field(min_length=2, max_length=200)
    urls: list[str] = Field(min_length=1, max_length=3)


class PeopleFound(BaseModel):
    people: list[PersonModel] = Field(max_length=MAX_PEOPLE)


def _url_key(url: str) -> str | None:
    """Tolerant key of an address: scheme and host in lowercase, no trailing `/` or fragment;
    path and query keep their case. `None` for a malformed address (`http://[abc`)."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _known_urls(state: CouncilState) -> dict[str, str]:
    """Addresses of the session (pages read, then results), by tolerant key."""
    known: dict[str, str] = {}
    for url in [p["url"] for p in state.get("pages", [])] + [
        h["url"] for h in state.get("hits", [])
    ]:
        if (key := _url_key(url)) is not None:
            known.setdefault(key, url)
    return known


def _kept_pages(state: CouncilState) -> list[dict[str, Any]]:
    """Selected pages, with the author read on the page."""
    pages = {p["source_id"]: p for p in state.get("pages", []) if p.get("source_id")}
    kept = []
    for verdict in state.get("verdicts", []):
        if verdict["verdict"] == "kept":
            page = pages.get(verdict["source_id"], {})
            kept.append({**verdict, "author": page.get("author")})
    return kept


def _pages_prompt(pages: list[dict[str, Any]]) -> str:
    blocks = []
    for page in pages:
        meta = "\n".join(
            [
                f"Title: {page_title(page)}",
                f"Author: {page.get('author') or 'unknown'}",
                f"URL: {page['url']}",
            ]
        )
        blocks.append(untrusted(meta, f"page {page['source_id']}"))
    return "\n\n".join(blocks)


def _vetted(found: PeopleFound, known: dict[str, str]) -> list[PersonFound]:
    """People with at least one address known to the session, no duplicate names. A malformed
    address is ignored: without another known address, the person is discarded."""
    people: list[PersonFound] = []
    names: set[str] = set()
    for person in found.people:
        keys = [key for raw in person.urls if (key := _url_key(raw)) is not None]
        urls = list(dict.fromkeys(u for key in keys if (u := known.get(key))))
        name = one_line(person.name)
        if not urls or name.casefold() in names:
            continue
        names.add(name.casefold())
        where = tuple(dict.fromkeys(urlsplit(u).hostname or u for u in urls))
        people.append(PersonFound(name, one_line(person.role), urls[0], where))
    return people[:MAX_PEOPLE]


async def _ask(deps: GraphDeps, state: CouncilState, pages: list[dict[str, Any]]) -> PeopleFound:
    prompt = render_prompt(
        AGENT,
        mode="people",
        query=state.get("query", ""),
        pages=_pages_prompt(pages),
        max_people=MAX_PEOPLE,
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        PeopleFound,
        [SystemMessage(prompt), HumanMessage("Find practitioners.")],
        agent=AGENT,
        step="praticiens",
        intent="looking for practitioners",
    )


def _emit_person(person: PersonFound, source_id: str) -> None:
    emit(
        "source.found",
        {
            "title": person.name,
            "url": person.url,
            "author": None,
            "date": None,
            "lang": None,
            "score": None,
            "source_id": source_id,
            "status": "ok",
            "verdict": "kept",
            "reason": None,
            "kind": "person",
            "role": person.role,
        },
        agent=AGENT,
    )


def _kept(person: PersonFound, source_id: str) -> dict[str, Any]:
    """Practitioner kept: reported (`source.found`) and returned for the state."""
    _emit_person(person, source_id)
    return {
        "source_id": source_id,
        "name": person.name,
        "role": person.role,
        "url": person.url,
        "where": list(person.where),
    }


def make_spot_people(deps: GraphDeps) -> Node:
    @node_timeout()
    async def spot_people(state: CouncilState) -> CouncilState:
        """Replayed after a stop (D84): the practitioners already recorded for the session are
        re-emitted as is, without a model call or an extra row (10 at most in all). Without a
        selected page: no model call. An invalid model output after the retries lets the
        Council continue without a practitioner (the search itself succeeded)."""
        known = await deps.web.people(deps.user_id, deps.session_id)
        if known:  # node replayed: the practitioners already recorded, without calling the model
            return {"people": [_kept(person, sid) for sid, person in known[:MAX_PEOPLE]]}
        pages = _kept_pages(state)
        if not pages:
            return {"people": []}
        try:
            found = await _ask(deps, state, pages)
        except AppError as exc:
            if exc.code != INVALID_OUTPUT_CODE:
                raise
            logger.warning("Practitioners not spotted (%s): session %s", exc.code, deps.session_id)
            return {"people": []}
        people: list[dict[str, Any]] = []
        for person in _vetted(found, _known_urls(state)):
            source_id = await deps.web.add_person(deps.user_id, deps.session_id, person)
            people.append(_kept(person, source_id))
        return {"people": people}

    return spot_people
