"""Partie pure du parcours `capture` (D108) : questions posées à January et lecture de ses
réponses, instantané des liens en JSON, nettoyage du résumé (références inconnues ignorées),
variables du prompt et textes annoncés. Aucune entrée-sortie ici."""

from dataclasses import asdict
from datetime import date
from typing import Any

from app.agents.prompts.loader import untrusted
from app.agents.tools.capture_port import (
    CaptureDigest,
    CaptureMaterial,
    CaptureSource,
    CaptureStored,
    ProgramLinks,
)
from app.agents.tools.replan_port import ModuleRef, TaskRef
from app.core.errors import AppError

AGENT = "archivist"
MAX_TEXT_CHARS = 20_000  # texte lu par l'Archiviste (page, document, texte collé)
CAPTURE_REQUEST = "Range cette capture."
UNREADABLE_TEXT = "Je n'arrive pas à lire ce lien. Colle son texte ci-dessous."
CANCELLED_TEXT = "Capture abandonnée."
CAPTURE_REASON = "Capture rapide de January."

CAPTURE_TEXT = "capture_text"
CAPTURE_TASK = "capture_task"
CAPTURE_CARDS = "capture_cards"
TEXT_INTERRUPT: dict[str, Any] = {
    "kind": CAPTURE_TEXT,
    "question": "Colle le texte de la page.",
    "fields": [
        {"id": "text", "label": "Texte de la page", "required": True, "max_length": MAX_TEXT_CHARS}
    ],
    "options": [{"value": "cancel", "label": "Abandonner"}],
}
YES_NO: list[dict[str, str]] = [{"value": "yes", "label": "Oui"}, {"value": "no", "label": "Non"}]


def document_not_indexed() -> AppError:
    return AppError("document_not_indexed", "Document pas encore indexé.", 409)


def source_of(state: dict[str, Any]) -> CaptureSource:
    """La source donnée au départ (`CaptureInput` en garantit une seule)."""
    if state.get("url"):
        return "url"
    return "document" if state.get("document_id") else "text"


# --- Réponses de January ------------------------------------------------------------------------


def parse_text(value: Any) -> str | None:
    """Le texte collé (`{"answers": {"text": …}}` ou `{"text": …}`), coupé à 20 000 caractères ;
    `None` : « Abandonner », un texte vide ou toute autre réponse."""
    if isinstance(value, dict):
        answers = value.get("answers")
        raw = answers.get("text") if isinstance(answers, dict) else value.get("text")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()[:MAX_TEXT_CHARS]
    return None


def parse_yes(value: Any) -> bool:
    """Oui : `"yes"`, `{"answer": "yes"}` ou `{"option": "yes"}` ; toute autre réponse : non."""
    if isinstance(value, dict):
        value = value.get("answer", value.get("option"))
    return isinstance(value, str) and value == "yes"


def task_payload(title: str) -> dict[str, Any]:
    question = f"Cette capture couvre « {' '.join(title.split())} ». La cocher ?"
    return {"kind": CAPTURE_TASK, "question": question, "options": YES_NO}


def cards_payload(fronts: list[str]) -> dict[str, Any]:
    head = "Créer cette fiche ?" if len(fronts) == 1 else f"Créer ces {len(fronts)} fiches ?"
    lines = "\n".join(f"- {' '.join(front.split())}" for front in fronts)
    return {"kind": CAPTURE_CARDS, "question": f"{head}\n{lines}", "options": YES_NO}


# --- Instantanés en JSON (état du graphe) -------------------------------------------------------


def material_json(material: CaptureMaterial) -> dict[str, Any]:
    return asdict(material)


def material_of(data: dict[str, Any]) -> CaptureMaterial:
    return CaptureMaterial(str(data["title"]), str(data["text"]), data.get("url"))


def _task_json(task: TaskRef) -> dict[str, Any]:
    return {**asdict(task), "planned_date": task.planned_date.isoformat()}


def _task_of(data: dict[str, Any]) -> TaskRef:
    return TaskRef(**{**data, "planned_date": date.fromisoformat(data["planned_date"])})


def links_json(links: ProgramLinks) -> dict[str, Any]:
    return {
        "modules": [asdict(m) for m in links.modules],
        "tasks": [_task_json(t) for t in links.tasks],
    }


def links_of(data: dict[str, Any]) -> ProgramLinks:
    return ProgramLinks(
        [ModuleRef(**m) for m in data.get("modules", [])],
        [_task_of(t) for t in data.get("tasks", [])],
    )


def stored_json(stored: CaptureStored) -> dict[str, Any]:
    task = stored.covered_task
    return {
        "memory_item_id": stored.memory_item_id,
        "journal_entry_id": stored.journal_entry_id,
        "covered_task": None if task is None else _task_json(task),
    }


# --- Résumé de l'Archiviste ---------------------------------------------------------------------


def clean_digest(digest: CaptureDigest, links: ProgramLinks, *, note: bool) -> CaptureDigest:
    """Lignes vides retirées (le titre à défaut), concepts et modules dédoublonnés, références
    inconnues ignorées ; `learned` n'est gardé que pour une note de January (jamais pour une
    page ou un document, qui pourrait le réclamer lui-même)."""
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
        }
    )


def unknown_refs(digest: CaptureDigest, links: ProgramLinks) -> int:
    """Nombre de références inconnues (journalisé, jamais les références elles-mêmes)."""
    modules = sum(links.module(ref) is None for ref in digest.modules)
    task = digest.covered_task is not None and links.task(digest.covered_task) is None
    return modules + int(task)


def _modules_text(links: ProgramLinks) -> str:
    if not links.modules:
        return "Aucun module."
    return "\n".join(
        f"{m.ref} : {' '.join(m.title.split())}"
        + (f" (compétences : {', '.join(m.skills)})" if m.skills else "")
        for m in links.modules
    )


def _tasks_text(links: ProgramLinks) -> str:
    if not links.tasks:
        return "Aucune tâche."
    return "\n".join(
        f"{t.ref} : {t.planned_date:%d/%m}, {' '.join(t.title.split())} "
        f"({t.type}, {t.minutes} min, module {t.module_ref})"
        for t in links.tasks
    )


_KINDS: dict[str, str] = {"url": "une page", "document": "un document", "text": "une note"}


def capture_vars(
    material: CaptureMaterial, links: ProgramLinks, *, source: CaptureSource, pasted: bool
) -> dict[str, Any]:
    """Variables du mode `capture` de `archivist.md` : tout contenu (page, document, note,
    programme) est encadré par `untrusted()` (17.4)."""
    return {
        "mode": "capture",
        "kind": "le texte collé d'une page" if pasted else _KINDS[source],
        "note": source == "text",
        "title": untrusted(" ".join(material.title.split()) or "(sans titre)", "titre"),
        "content": untrusted(material.text[:MAX_TEXT_CHARS], "capture"),
        "modules": untrusted(_modules_text(links), "programme:modules"),
        "tasks": untrusted(_tasks_text(links), "programme:taches"),
    }


# --- Textes annoncés ----------------------------------------------------------------------------


def digest_text(digest: CaptureDigest) -> str:
    lines = "\n".join(f"- {line}" for line in digest.summary)
    return f"« {digest.title} »\n{lines}"


def _cards_text(count: int) -> str:
    if count == 0:
        return ""
    return " 1 fiche créée." if count == 1 else f" {count} fiches créées."


def end_text(title: str, ticked: str | None, cards: int) -> str:
    task = f" Tâche « {' '.join(ticked.split())} » cochée." if ticked else ""
    return f"Capture rangée dans ta mémoire : « {title} ».{task}{_cards_text(cards)}"
