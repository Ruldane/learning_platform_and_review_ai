"""The Archivist in `profile` mode (SPEC 5.1, D124): from the CV, the LinkedIn profile and
January's note, it extracts the draft of the master profile. Flow `cv_capture`, `profile` mode.

`load_sources` reads the visible text of the PDFs through the port (invisible text set aside);
`extract` asks for the profile (each source wrapped by `untrusted`, 17.4), erases the ids and
sources returned by the model and sets provisional ids; `check` (code only) removes the lines
whose figure is in no document and the facts that cannot be found, then sets the sources;
`save_draft` files the draft (idempotent per session); `announce` says so.

Logs: identifiers and numbers only, never a line of the profile or of a document
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
LOAD_TIMEOUT_S = 180  # two PDF layouts (60 s each at most) and their reading
EXTRACT_TIMEOUT_S = 600  # a long structured output (GLM), with its retries
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
            {"step": "lecture", "intent": "I am reading your documents"},
            agent=AGENT,
        )
        found = await deps.ports.profile.sources(
            deps.user_id, state.get("document_ids", []), state.get("note")
        )
        if not any(source.text.strip() for source in found.sources):
            raise no_text()
        logger.info(
            "Profile sources read: session %s, %d source(s), %d invisible line(s)",
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
        """The Archivist's profile, model ids and sources erased, provisional ids set."""
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
    """Code only: figures not found, facts not found, sources set."""
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
            "Profile draft stored: session %s, version %d, %d line(s) removed",
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
