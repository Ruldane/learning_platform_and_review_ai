"""L'Archiviste range une capture rapide (SPEC F18, D108) : parcours `capture`.

`read` lit la source sans appeler le modèle : un lien par `web_read` (garde SSRF, cache, 15 s au
plus), un document importé par le port (toutes les 3 s, 90 s au plus), un texte tel quel. Un lien
illisible est signalé tout de suite (message, puis question `capture_text`). `digest` fait
résumer la capture (texte encadré par `untrusted`) et ignore les références inconnues ; `store`
la range par le port (idempotent par session). Les questions (`ask_text`, `ask_task`,
`ask_cards`) ne font qu'`interrupt()`, puis lisent la réponse (rien avant l'arrêt, SPEC 9.4) ; la
tâche n'est cochée et les fiches créées qu'après un oui.

Journaux : identifiants et nombres seulement, jamais l'adresse, le titre ni le texte capturé."""

import asyncio
import logging
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.nodes.archivist_capture_steps import (
    AGENT,
    CANCELLED_TEXT,
    CAPTURE_REASON,
    CAPTURE_REQUEST,
    MAX_TEXT_CHARS,
    TEXT_INTERRUPT,
    UNREADABLE_TEXT,
    capture_vars,
    cards_payload,
    clean_digest,
    digest_text,
    document_not_indexed,
    end_text,
    links_json,
    links_of,
    material_json,
    material_of,
    parse_text,
    parse_yes,
    source_of,
    stored_json,
    task_payload,
    unknown_refs,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.capture import CaptureState
from app.agents.tools.capture_port import CaptureDigest, CaptureMaterial, is_note
from app.agents.tools.study_schema import CardDraft
from app.agents.tools.web_tools import web_read
from app.core.errors import AppError

READ_TIMEOUT_S = 15.0  # lecture d'un lien
DOC_POLL_S = 3.0  # document pas encore indexé : nouvel essai
DOC_WAIT_S = 90.0  # puis « Document pas encore indexé. »
DIGEST_TIMEOUT_S = 300
STORE_TIMEOUT_S = 300  # vectorisation de l'élément et reflet des acquis

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CaptureState) -> CaptureState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


async def _read_url(deps: GraphDeps, url: str) -> CaptureMaterial | None:
    """La page lue, ou `None` : illisible, refusée (garde SSRF), plafond atteint, trop lente."""
    try:
        async with asyncio.timeout(READ_TIMEOUT_S):
            page = await web_read(deps, url, agent=AGENT)
    except (TimeoutError, AppError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        logger.info("Capture : lien non lu (session %s, %s)", deps.session_id, code)
        return None
    if page.status != "ok" or not page.text.strip():
        logger.info("Capture : lien illisible (session %s)", deps.session_id)
        return None
    return CaptureMaterial(page.title or "", page.text[:MAX_TEXT_CHARS], page.url)


async def _read_document(deps: GraphDeps, document_id: str) -> CaptureMaterial:
    """Le document dès qu'il est indexé ; au-delà de `DOC_WAIT_S` : run.failed."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + DOC_WAIT_S
    while True:
        found = await deps.ports.capture.document(deps.user_id, document_id)
        if found is not None:
            return CaptureMaterial(found.title, found.text[:MAX_TEXT_CHARS], found.url)
        if loop.time() + DOC_POLL_S > deadline:
            logger.info("Capture : document %s pas encore indexé", document_id)
            raise document_not_indexed()
        await asyncio.sleep(DOC_POLL_S)


def make_read(deps: GraphDeps) -> Node:
    @node_timeout(DOC_WAIT_S + 30)
    async def read(state: CaptureState) -> CaptureState:
        emit("agent.started", {"step": "lecture", "intent": "je lis ta capture"}, agent=AGENT)
        source = source_of(dict(state))
        if source == "url":
            page = await _read_url(deps, state["url"] or "")
            if page is None:
                _say("capture-illisible", UNREADABLE_TEXT)
                return {"source": source, "unreadable": True}
            return {"source": source, "unreadable": False, "material": material_json(page)}
        if source == "document":
            found = await _read_document(deps, state["document_id"] or "")
            return {"source": source, "unreadable": False, "material": material_json(found)}
        note = CaptureMaterial("", (state.get("text") or "")[:MAX_TEXT_CHARS], None)
        return {"source": source, "unreadable": False, "material": material_json(note)}

    return read


def route_read(state: CaptureState) -> str:
    return "ask_text" if state.get("unreadable") else "digest"


def ask_text(state: CaptureState) -> CaptureState:
    """Point d'arrêt : le texte de la page illisible, ou « Abandonner »."""
    text = parse_text(interrupt(TEXT_INTERRUPT))
    if text is None:
        _say("capture-fin", CANCELLED_TEXT)
        return {"outcome": "cancelled", "summary": CANCELLED_TEXT}
    material = CaptureMaterial("", text, state.get("url"))
    return {"material": material_json(material), "pasted": True, "unreadable": False}


def route_text(state: CaptureState) -> str:
    return "end" if state.get("outcome") == "cancelled" else "digest"


def make_digest(deps: GraphDeps) -> Node:
    @node_timeout(DIGEST_TIMEOUT_S)
    async def digest(state: CaptureState) -> CaptureState:
        """Le résumé de l'Archiviste, relié aux modules et aux tâches de l'instantané."""
        links = await deps.ports.capture.links(deps.user_id)
        source = source_of(dict(state))
        material = material_of(state["material"])
        variables = capture_vars(material, links, source=source, pasted=state.get("pasted", False))
        prompt = render_prompt(AGENT, **variables)
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        found = await structured_call(
            model,
            CaptureDigest,
            [SystemMessage(prompt), HumanMessage(CAPTURE_REQUEST)],
            agent=AGENT,
            step="capture",
            intent="je résume ta capture et la relie à ton programme",
        )
        if unknown := unknown_refs(found, links):
            logger.info(
                "Capture : %d référence(s) inconnue(s) ignorée(s) (session %s)",
                unknown,
                deps.session_id,
            )
        clean = clean_digest(found, links, note=is_note(source, material.text))
        return {"links": links_json(links), "digest": clean.model_dump(mode="json")}

    return digest


def make_store(deps: GraphDeps) -> Node:
    @node_timeout(STORE_TIMEOUT_S)
    async def store(state: CaptureState) -> CaptureState:
        """La capture rangée par le port (idempotent par session), puis annoncée."""
        found = CaptureDigest.model_validate(state["digest"])
        stored = await deps.ports.capture.store(
            deps.user_id,
            deps.session_id,
            found,
            material_of(state["material"]),
            links_of(state["links"]),
            source=source_of(dict(state)),
        )
        logger.info(
            "Capture rangée : session %s, élément %s, journal %s, tâche couverte %s, "
            "%d fiche(s) proposée(s), acquis déclarés %s",
            deps.session_id,
            stored.memory_item_id,
            stored.journal_entry_id,
            stored.covered_task is not None,
            len(found.flashcards),
            found.learned,
        )
        _say("capture-resume", digest_text(found))
        written = {
            "item_id": stored.memory_item_id,
            "kind": "document",
            "title": found.title,
            "reason": CAPTURE_REASON,
        }
        emit("memory.written", written, agent=AGENT)
        return {"stored": stored_json(stored)}

    return store


def route_store(state: CaptureState) -> str:
    return "ask_task" if state["stored"].get("covered_task") else "after_task"


def ask_task(state: CaptureState) -> CaptureState:
    """Point d'arrêt : cocher la tâche que la capture couvre ?"""
    task = state["stored"]["covered_task"]
    return {"tick": parse_yes(interrupt(task_payload(task["title"])))}


def route_task(state: CaptureState) -> str:
    return "tick" if state.get("tick") else "after_task"


def make_tick(deps: GraphDeps) -> Node:
    @node_timeout()
    async def tick(state: CaptureState) -> CaptureState:
        """L'id vient de l'instantané gardé dans l'état (F7), jamais du modèle."""
        task_id = state["stored"]["covered_task"]["task_id"]
        ticked = await deps.ports.capture.tick_task(deps.user_id, deps.session_id, task_id)
        logger.info(
            "Capture : tâche %s %s (session %s)",
            task_id,
            "cochée" if ticked else "introuvable",
            deps.session_id,
        )
        return {"ticked": ticked}

    return tick


def after_task(state: CaptureState) -> CaptureState:
    return {}


def route_after_task(state: CaptureState) -> str:
    return "ask_cards" if state["digest"].get("flashcards") else "finalize"


def ask_cards(state: CaptureState) -> CaptureState:
    """Point d'arrêt : créer les fiches proposées (rectos montrés) ?"""
    fronts = [str(card["front"]) for card in state["digest"]["flashcards"]]
    return {"want_cards": parse_yes(interrupt(cards_payload(fronts)))}


def route_cards(state: CaptureState) -> str:
    return "cards" if state.get("want_cards") else "finalize"


def make_cards(deps: GraphDeps) -> Node:
    @node_timeout()
    async def cards(state: CaptureState) -> CaptureState:
        drafts = [CardDraft.model_validate(card) for card in state["digest"]["flashcards"]]
        created = await deps.ports.capture.add_cards(deps.user_id, deps.session_id, drafts)
        logger.info("Capture : %d fiche(s) créée(s) (session %s)", created, deps.session_id)
        return {"cards_created": created}

    return cards


def finalize(state: CaptureState) -> CaptureState:
    task = state["stored"].get("covered_task")
    ticked = str(task["title"]) if task and state.get("ticked") else None
    text = end_text(state["digest"]["title"], ticked, state.get("cards_created", 0))
    _say("capture-fin", text)
    return {"summary": text}
