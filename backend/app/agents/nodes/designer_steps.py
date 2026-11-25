"""Pure rules of the Layout designer (D125): demonstration content copied as is, `cv_template`
question and parsing of January's answer. No port, no model.

A line of the content "appears" in the CV if its text is found in the visible text of the PDF
after normalizing the **form** only: Unicode NFKC (ligatures), case, spaces and line breaks
(a line split in the PDF), typographic dashes and apostrophes. No word may change: the model
copies, it does not write."""

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.agents.prompts.loader import untrusted
from app.agents.tools.cv_schema import CvContent, CvEntry, CvLine, CvSection

MAX_ADJUSTMENTS = 5  # January's instructions, outside the automatic passes
MAX_INSTRUCTION_CHARS = 500
MAX_INVENTED_SHOWN = 20  # lines quoted to the model when it copies them wrongly

_SPACES = re.compile(r"\s+")
_DASHES = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-", "’": "'", "‘": "'"})


def plain(text: str) -> str:
    """Normalized form of a text (see the header): only the form changes, never a word."""
    text = unicodedata.normalize("NFKC", text).translate(_DASHES).casefold()
    return _SPACES.sub(" ", text).strip()


def _entry_texts(entry: CvEntry) -> list[str]:
    texts = [entry.heading, entry.subheading or "", entry.dates or ""]
    return texts + [line.text for line in entry.lines]


def sample_texts(content: CvContent) -> list[str]:
    """Every text of the content: name, tagline, contacts, titles, entries, lines."""
    texts = [content.name, content.headline or "", *content.contact]
    for section in content.sections:
        texts.append(section.title)
        for entry in section.entries:
            texts += _entry_texts(entry)
        texts += [item.text for item in section.items]
    return [text for text in texts if text.strip()]


def invented_lines(content: CvContent, original_text: str) -> list[str]:
    """The texts of the content absent from the visible CV text (no duplicates, in order)."""
    hay = plain(original_text)
    return list(dict.fromkeys(t for t in sample_texts(content) if plain(t) not in hay))


def _lines(lines: list[CvLine], invented: set[str]) -> list[CvLine]:
    return [CvLine(text=line.text) for line in lines if line.text not in invented]


def _entry(entry: CvEntry, invented: set[str]) -> CvEntry | None:
    kept = CvEntry(
        heading="" if entry.heading in invented else entry.heading,
        subheading=None if entry.subheading in invented else entry.subheading,
        dates=None if entry.dates in invented else entry.dates,
        lines=_lines(entry.lines, invented),
    )
    return kept if kept.heading or kept.subheading or kept.dates or kept.lines else None


def _section(section: CvSection, invented: set[str]) -> CvSection | None:
    """A section with an invented title is removed with its content (a title is mandatory)."""
    if section.title in invented:
        return None
    entries = [e for e in (_entry(entry, invented) for entry in section.entries) if e]
    items = _lines(section.items, invented)
    if not entries and not items:
        return None
    return CvSection(key=section.key, title=section.title, entries=entries, items=items)


def verbatim(content: CvContent, invented: list[str]) -> CvContent:
    """The content without the `invented` texts, empty sections and entries removed; the
    `fact_ids` are erased (a demonstration is backed by no fact of the profile)."""
    out = set(invented)
    sections = [s for s in (_section(section, out) for section in content.sections) if s]
    return CvContent(
        name="" if content.name in out else content.name,
        headline=None if content.headline in out else content.headline,
        contact=[item for item in content.contact if item not in out],
        sections=sections,
    )


def copy_retry(invented: list[str]) -> str:
    """The re-request: these texts are near-exact copies of CV lines, hence untrusted (17.4);
    only the instruction stays outside the wrapper."""
    shown = "\n".join(f"- {text}" for text in invented[:MAX_INVENTED_SHOWN])
    return (
        "These texts do not appear as is in the CV:\n"
        f"{untrusted(shown, 'cv:texts to copy')}\n"
        "Copy each text word for word from the CV (without a bullet or a dash at the start of the "
        "line), or remove it. Return the complete content."
    )


def spec_retry(problems: list[str]) -> str:
    listed = "\n".join(f"- {problem}" for problem in problems)
    return (
        f"Your description has these defects:\n{listed}\n"
        "Fix them and return the complete description."
    )


# --- Question `cv_template` (preflight G9) -------------------------------------------------------

_VALIDATE = {"value": "validate", "label": "Approve"}
_ADJUST = {"value": "adjust", "label": "Adjust"}
_RESTART = {"value": "restart", "label": "Restart the capture"}
_INSTRUCTION = {
    "id": "instruction",
    "label": "What to change",
    "max_length": MAX_INSTRUCTION_CHARS,
}


def question(score: int, adjustments: int) -> dict[str, Any]:
    """The question asked after the passes, whatever the score; at the 5th adjustment, only
    "Approve" and "Restart the capture" remain."""
    text = f"The template matches your CV at {score}%. Do you approve it?"
    if adjustments >= MAX_ADJUSTMENTS:
        return {
            "kind": "cv_template",
            "question": f"{text} You have made all {MAX_ADJUSTMENTS} possible adjustments.",
            "options": [_VALIDATE, _RESTART],
            "fields": [],
        }
    return {
        "kind": "cv_template",
        "question": text,
        "options": [_VALIDATE, _ADJUST, _RESTART],
        "fields": [_INSTRUCTION],
    }


class DesignAnswer(BaseModel):
    action: Literal["validate", "adjust", "restart"]
    instruction: str = Field(default="", max_length=MAX_INSTRUCTION_CHARS)


def _as_action(value: dict[str, Any]) -> dict[str, Any] | None:
    if "action" in value:
        return value
    answers = value.get("answers")
    if not isinstance(answers, dict) or not isinstance(answers.get("instruction"), str):
        return None
    return {"action": "adjust", "instruction": answers["instruction"]}


def parse_answer(value: Any, adjustments: int) -> DesignAnswer | None:
    """`"validate"`, `"restart"`, `{"answers": {"instruction": ...}}` or `{"action": ...,
    "instruction": ...}`. The instruction is cut at 500 characters rather than refused. `None`
    (the question is asked again): unknown shape, adjustment without instruction, or beyond the
    5th."""
    if value in ("validate", "restart"):
        return DesignAnswer(action=value)
    if not isinstance(value, dict) or (data := _as_action(value)) is None:
        return None
    if isinstance(data.get("instruction"), str):
        data = {**data, "instruction": data["instruction"].strip()[:MAX_INSTRUCTION_CHARS]}
    try:
        answer = DesignAnswer.model_validate(data)
    except ValidationError:
        return None
    if answer.action != "adjust":
        return DesignAnswer(action=answer.action)
    if not answer.instruction or adjustments >= MAX_ADJUSTMENTS:
        return None
    return answer
