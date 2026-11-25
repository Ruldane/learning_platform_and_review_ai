"""Pure part of the `capture` flow (D108): questions asked to January and reading of her
answers, snapshot of the links in JSON, cleaning of the summary (unknown references ignored),
prompt variables and announced texts. No input/output here."""

from dataclasses import asdict
from typing import Any

from app.agents.prompts.loader import untrusted
from app.agents.tools.capture_port import (
    CAPTURE_REASON as CAPTURE_REASON,
)
from app.agents.tools.capture_port import (
    CaptureDigest,
    CaptureMaterial,
    CaptureSource,
    CaptureStored,
    ProgramLinks,
    is_note,
)
from app.agents.tools.replan_port import ModuleRef, TaskRef
from app.core.errors import AppError

AGENT = "archivist"
MAX_TEXT_CHARS = 20_000  # text read by the Archivist (page, document, pasted text)
CAPTURE_REQUEST = "Summarize and save this capture."
UNREADABLE_TEXT = "I couldn't read the link. Paste the page text below."
CANCELLED_TEXT = "Capture cancelled."

CAPTURE_TEXT = "capture_text"
CAPTURE_TASK = "capture_task"
CAPTURE_CARDS = "capture_cards"
TEXT_INTERRUPT: dict[str, Any] = {
    "kind": CAPTURE_TEXT,
    "question": "Paste the page text.",
    "fields": [
        {"id": "text", "label": "Page text", "required": True, "max_length": MAX_TEXT_CHARS}
    ],
    "options": [{"value": "cancel", "label": "Cancel"}],
}
YES_NO: list[dict[str, str]] = [{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}]


def document_not_indexed() -> AppError:
    return AppError("document_not_indexed", "This document is not indexed yet.", 409)


def source_of(state: dict[str, Any]) -> CaptureSource:
    """The source given at the start (`CaptureInput` guarantees a single one)."""
    if state.get("url"):
        return "url"
    return "document" if state.get("document_id") else "text"


# --- January's answers --------------------------------------------------------------------------


def parse_text(value: Any) -> str | None:
    """The pasted text (`{"answers": {"text": ...}}` or `{"text": ...}`), cut at 20,000
    characters; `None`: "Cancel", an empty text or any other answer."""
    if isinstance(value, dict):
        answers = value.get("answers")
        raw = answers.get("text") if isinstance(answers, dict) else value.get("text")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()[:MAX_TEXT_CHARS]
    return None


def parse_yes(value: Any) -> bool:
    """Yes: `"yes"`, `{"answer": "yes"}` or `{"option": "yes"}`; any other answer: no."""
    if isinstance(value, dict):
        value = value.get("answer", value.get("option"))
    return isinstance(value, str) and value == "yes"


def task_payload(title: str) -> dict[str, Any]:
    question = f"This capture covers “{' '.join(title.split())}.” Mark that task complete?"
    return {"kind": CAPTURE_TASK, "question": question, "options": YES_NO}


def cards_payload(fronts: list[str]) -> dict[str, Any]:
    head = (
        "Create this flashcard?" if len(fronts) == 1 else f"Create these {len(fronts)} flashcards?"
    )
    lines = "\n".join(f"- {' '.join(front.split())}" for front in fronts)
    return {"kind": CAPTURE_CARDS, "question": f"{head}\n{lines}", "options": YES_NO}


# --- JSON snapshots (graph state) ---------------------------------------------------------------


def material_json(material: CaptureMaterial) -> dict[str, Any]:
    return asdict(material)


def material_of(data: dict[str, Any]) -> CaptureMaterial:
    return CaptureMaterial(str(data["title"]), str(data["text"]), data.get("url"))


def _task_json(task: TaskRef) -> dict[str, Any]:
    return {**asdict(task), "planned_date": task.planned_date.isoformat()}


def links_json(links: ProgramLinks) -> dict[str, Any]:
    return {
        "modules": [asdict(m) for m in links.modules],
        "tasks": [_task_json(t) for t in links.tasks],
    }


def links_of(data: dict[str, Any]) -> ProgramLinks:
    return ProgramLinks(
        [ModuleRef(**m) for m in data.get("modules", [])],
        [TaskRef.from_checkpoint(t) for t in data.get("tasks", [])],
    )


def stored_json(stored: CaptureStored) -> dict[str, Any]:
    task = stored.covered_task
    return {
        "memory_item_id": stored.memory_item_id,
        "journal_entry_id": stored.journal_entry_id,
        "covered_task": None if task is None else _task_json(task),
    }


# --- Archivist summary --------------------------------------------------------------------------


def clean_digest(digest: CaptureDigest, links: ProgramLinks, *, note: bool) -> CaptureDigest:
    """Empty lines removed (the title by default), concepts and modules deduplicated, unknown
    references ignored; `learned` is kept only for a note from January (never for a page or a
    document, which could claim it itself). The cards lose their skill: a name taken from
    untrusted content must never be able to downgrade an acquired skill (like the session cards,
    D103 no. 11; final review of phase 5, A-I2)."""
    summary = [" ".join(line.split()) for line in digest.summary if line.strip()]
    concepts = list(dict.fromkeys(c.strip() for c in digest.concepts if c.strip()))
    modules = [ref for ref in dict.fromkeys(digest.modules) if links.module(ref) is not None]
    task = digest.covered_task if digest.covered_task and links.task(digest.covered_task) else None
    return digest.model_copy(
        update={
            "summary": summary or [digest.title],
            "concepts": concepts,
            "modules": modules,
            "covered_task": task,
            "learned": digest.learned and note,
            "flashcards": [c.model_copy(update={"skill": None}) for c in digest.flashcards],
        }
    )


def unknown_refs(digest: CaptureDigest, links: ProgramLinks) -> int:
    """Number of unknown references (logged, never the references themselves)."""
    modules = sum(links.module(ref) is None for ref in digest.modules)
    task = digest.covered_task is not None and links.task(digest.covered_task) is None
    return modules + int(task)


def _modules_text(links: ProgramLinks) -> str:
    if not links.modules:
        return "No modules."
    return "\n".join(
        f"{m.ref}: {' '.join(m.title.split())}"
        + (f" (skills: {', '.join(m.skills)})" if m.skills else "")
        for m in links.modules
    )


def _tasks_text(links: ProgramLinks) -> str:
    if not links.tasks:
        return "No tasks."
    return "\n".join(
        f"{t.ref}: {t.planned_date.isoformat()}, {' '.join(t.title.split())} "
        f"({t.type}, {t.minutes} min, module {t.module_ref})"
        for t in links.tasks
    )


_KINDS: dict[str, str] = {"url": "a page", "document": "a document", "text": "a note"}


def _kind(material: CaptureMaterial, source: CaptureSource, pasted: bool) -> str:
    if pasted:
        return "pasted page text"
    if source == "text" and not is_note(source, material.text):
        return "pasted text"
    return _KINDS[source]


def capture_vars(
    material: CaptureMaterial, links: ProgramLinks, *, source: CaptureSource, pasted: bool
) -> dict[str, Any]:
    """Variables of the `capture` mode of `archivist.md`: any content (page, document, note,
    program) is wrapped by `untrusted()` (17.4)."""
    return {
        "mode": "capture",
        "kind": _kind(material, source, pasted),
        "note": is_note(source, material.text),
        "title": untrusted(" ".join(material.title.split()) or "(untitled)", "title"),
        "content": untrusted(material.text[:MAX_TEXT_CHARS], "capture"),
        "modules": untrusted(_modules_text(links), "program:modules"),
        "tasks": untrusted(_tasks_text(links), "program:tasks"),
    }


# --- Announced texts ----------------------------------------------------------------------------


def digest_text(digest: CaptureDigest) -> str:
    lines = "\n".join(f"- {line}" for line in digest.summary)
    return f"“{digest.title}”\n{lines}"


def _cards_text(count: int) -> str:
    if count == 0:
        return ""
    return " Created 1 flashcard." if count == 1 else f" Created {count} flashcards."


def end_text(title: str, ticked: str | None, cards: int) -> str:
    task = f" Marked “{' '.join(ticked.split())}” complete." if ticked else ""
    return f"Saved “{title}” to memory.{task}{_cards_text(cards)}"
