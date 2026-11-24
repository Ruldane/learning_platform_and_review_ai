"""L'Archiviste en mode `profile` (SPEC 5.1, D124) : du CV, du profil LinkedIn et de la note de
January, il tire le brouillon du profil maître. Parcours `cv_capture`, mode `profile`.

`load_sources` lit le texte visible des PDF par le port (texte invisible mis de côté) ;
`extract` demande le profil (chaque source encadrée par `untrusted`, 17.4), efface les ids et
les sources rendus par le modèle et pose des ids provisoires ; `check` (code seul) retire les
lignes dont un chiffre n'est dans aucun document et les faits introuvables, puis pose les
sources ; `save_draft` range le brouillon (idempotent par session) ; `announce` le dit.

Journaux : identifiants et nombres seulement, jamais une ligne du profil ni d'un document
(17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.cv_capture import CvCaptureState
from app.agents.tools.cv_schema import MasterProfileData, assign_fact_ids, facts_of
from app.agents.tools.profile_check import (
    blank_facts,
    removed_facts,
    tag_sources,
    unsupported_lines,
    untraced_lines,
    without_lines,
)
from app.agents.tools.profile_port import ProfileSource, SourceKind
from app.core.errors import AppError

AGENT = "archivist"
PROFILE_REQUEST = "Build January's master profile from her documents."
LOAD_TIMEOUT_S = 180  # deux mises en page de PDF (60 s chacune au plus) et leur lecture
EXTRACT_TIMEOUT_S = 600  # une longue sortie structurée (GLM), avec ses nouveaux essais
ARTIFACT_URL = "/career/profile"
_KINDS: dict[str, SourceKind] = {"cv": "cv", "linkedin": "linkedin", "note": "note"}

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvCaptureState) -> CvCaptureState: ...


def no_text() -> AppError:
    return AppError(
        "profile_no_text",
        "No readable text was found. Export your CV as a PDF with selectable text and try again.",
        422,
    )


def _sources(state: CvCaptureState) -> list[ProfileSource]:
    return [ProfileSource(_KINDS[s["kind"]], s["text"]) for s in state.get("sources", [])]


def make_load_sources(deps: GraphDeps) -> Node:
    @node_timeout(LOAD_TIMEOUT_S)
    async def load_sources(state: CvCaptureState) -> CvCaptureState:
        emit(
            "agent.started",
            {"step": "lecture", "intent": "je lis tes documents"},
            agent=AGENT,
        )
        found = await deps.ports.profile.sources(
            deps.user_id, state.get("document_ids", []), state.get("note")
        )
        if not any(source.text.strip() for source in found.sources):
            raise no_text()
        logger.info(
            "Sources du profil lues : session %s, %d source(s), %d ligne(s) invisible(s)",
            deps.session_id,
            len(found.sources),
            len(found.hidden),
        )
        return {
            "sources": [{"kind": s.kind, "text": s.text} for s in found.sources],
            "hidden": list(found.hidden),
        }

    return load_sources


def _documents(sources: list[ProfileSource]) -> str:
    return "\n\n".join(untrusted(source.text, source.kind) for source in sources)


def make_extract(deps: GraphDeps) -> Node:
    @node_timeout(EXTRACT_TIMEOUT_S)
    async def extract(state: CvCaptureState) -> CvCaptureState:
        """Le profil de l'Archiviste, ids et sources du modèle effacés, ids provisoires posés."""
        sources = _sources(state)
        kinds = {source.kind for source in sources}
        prompt = render_prompt(
            AGENT,
            mode="profile",
            sources=_documents(sources),
            has_linkedin="linkedin" in kinds,
            has_note="note" in kinds,
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        found = await structured_call(
            model,
            MasterProfileData,
            [SystemMessage(prompt), HumanMessage(PROFILE_REQUEST)],
            agent=AGENT,
            step="profil",
            intent="building your master profile from your documents",
        )
        draft = assign_fact_ids(blank_facts(found))
        return {"draft": draft.model_dump(mode="json")}

    return extract


def check(state: CvCaptureState) -> CvCaptureState:
    """Code seul : chiffres introuvables, faits introuvables, sources posées."""
    sources = _sources(state)
    draft = MasterProfileData.model_validate(state["draft"])
    bad = unsupported_lines(draft, sources)
    loose = [line_id for line_id in untraced_lines(draft, sources) if line_id not in bad]
    facts = facts_of(draft)
    cleaned = without_lines(draft, [*bad, *loose])
    tagged = tag_sources(cleaned, sources)
    untraced = removed_facts(cleaned, tagged)
    hidden = state.get("hidden", [])
    return {
        "draft": tagged.model_dump(mode="json"),
        "dropped": [facts[line_id] for line_id in [*bad, *loose]] + untraced + list(hidden),
        "unsupported": len(bad),
        "untraced": len(loose) + len(untraced),
    }


def make_save_draft(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save_draft(state: CvCaptureState) -> CvCaptureState:
        draft = MasterProfileData.model_validate(state["draft"])
        version = await deps.ports.profile.save_draft(
            deps.user_id, deps.session_id, draft, state.get("dropped", [])
        )
        logger.info(
            "Brouillon du profil rangé : session %s, version %d, %d ligne(s) retirée(s)",
            deps.session_id,
            version,
            len(state.get("dropped", [])),
        )
        return {"version": version}

    return save_draft


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def announce_text(state: CvCaptureState) -> str:
    """Summarize the draft profile and the claims omitted from it."""
    draft = MasterProfileData.model_validate(state["draft"])
    parts = [
        "Your master profile is ready to review with "
        f"{_count(len(draft.experiences), 'role', 'roles')} and "
        f"{_count(len(draft.skills), 'skill', 'skills')}."
    ]
    if n := state.get("unsupported", 0):
        removed = _count(n, "line", "lines")
        parts.append(f"Removed {removed} with numbers missing from your documents.")
    if n := state.get("untraced", 0):
        removed = _count(n, "fact", "facts")
        parts.append(f"Removed {removed} missing from your documents.")
    if n := len(state.get("hidden", [])):
        hidden = _count(n, "line", "lines")
        parts.append(f"Ignored {hidden} of hidden text in your documents.")
    return " ".join(parts)


def announce(state: CvCaptureState) -> CvCaptureState:
    text = announce_text(state)
    emit("agent.message", {"message_id": f"{AGENT}-profil", "text": text}, agent=AGENT)
    artifact = {
        "artifact_id": f"profil-v{state['version']}",
        "kind": "master_profile",
        "title": "Master profile",
        "url": ARTIFACT_URL,
    }
    emit("artifact.ready", artifact, agent=AGENT)
    return {"summary": text}
