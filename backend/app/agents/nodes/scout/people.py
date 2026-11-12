"""L'Éclaireur repère des praticiens (SPEC 10.3, D84) : de vraies personnes qui publient sur le
sujet, 10 au plus, avec leur nom, leur rôle et où elles publient. Informations professionnelles
publiques seulement.

Le modèle ne voit que les pages retenues (titre, auteur, adresse, encadrés comme non fiables).
Une personne n'est gardée que si au moins une de ses adresses est une page lue ou un résultat de
la session : l'adresse enregistrée est alors celle de la session, jamais celle que le modèle a
écrite. Une personne sans adresse connue est écartée : jamais inventée."""

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
    role: str = Field(min_length=2, max_length=200)
    urls: list[str] = Field(min_length=1, max_length=3)


class PeopleFound(BaseModel):
    people: list[PersonModel] = Field(max_length=MAX_PEOPLE)


def _url_key(url: str) -> str:
    """Clé tolérante d'une adresse : schéma et hôte en minuscules, sans `/` final ni fragment ;
    chemin et requête gardent leur casse."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _known_urls(state: CouncilState) -> dict[str, str]:
    """Adresses de la session (pages lues, puis résultats), par clé tolérante."""
    known: dict[str, str] = {}
    for url in [p["url"] for p in state.get("pages", [])] + [
        h["url"] for h in state.get("hits", [])
    ]:
        known.setdefault(_url_key(url), url)
    return known


def _kept_pages(state: CouncilState) -> list[dict[str, Any]]:
    """Pages retenues, avec l'auteur lu sur la page."""
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
                f"Titre : {page_title(page)}",
                f"Auteur : {page.get('author') or 'inconnu'}",
                f"Adresse : {page['url']}",
            ]
        )
        blocks.append(untrusted(meta, f"page {page['source_id']}"))
    return "\n\n".join(blocks)


def _vetted(found: PeopleFound, known: dict[str, str]) -> list[PersonFound]:
    """Personnes dont au moins une adresse est connue de la session, sans doublon de nom."""
    people: list[PersonFound] = []
    names: set[str] = set()
    for person in found.people:
        urls = list(dict.fromkeys(u for raw in person.urls if (u := known.get(_url_key(raw)))))
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
        [SystemMessage(prompt), HumanMessage("Repère les praticiens.")],
        agent=AGENT,
        step="praticiens",
        intent="je repère des praticiens",
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
    """Praticien gardé : signalé (`source.found`) et rendu pour l'état."""
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
        """Rejoué après un arrêt (D84) : les praticiens déjà enregistrés pour la session sont
        réémis tels quels, sans appel au modèle ni ligne de plus (10 au plus en tout). Sans page
        retenue : aucun appel au modèle. Une sortie du modèle invalide après les essais laisse
        le Conseil continuer sans praticien (la recherche, elle, a abouti)."""
        known = await deps.web.people(deps.user_id, deps.session_id)
        if known:  # nœud rejoué : les praticiens déjà enregistrés, sans rappeler le modèle
            return {"people": [_kept(person, sid) for sid, person in known[:MAX_PEOPLE]]}
        pages = _kept_pages(state)
        if not pages:
            return {"people": []}
        try:
            found = await _ask(deps, state, pages)
        except AppError as exc:
            if exc.code != INVALID_OUTPUT_CODE:
                raise
            logger.warning("Praticiens non repérés (%s) : session %s", exc.code, deps.session_id)
            return {"people": []}
        people: list[dict[str, Any]] = []
        for person in _vetted(found, _known_urls(state)):
            source_id = await deps.web.add_person(deps.user_id, deps.session_id, person)
            people.append(_kept(person, source_id))
        return {"people": people}

    return spot_people
