"""What the nodes of the `lesson_factory` flow share: the shape of a node and the selected,
numbered sources. A source is admitted into a lesson if it is read and scored 60 or more
(SPEC 10.3): these are the session's "kept" verdicts, never an address written by a
model."""

from dataclasses import dataclass
from typing import Any, Protocol

from app.agents.nodes.lesson_reference import source_url_key
from app.agents.nodes.scout.models import one_line, page_title
from app.agents.prompts.loader import untrusted
from app.agents.state.lesson_factory import LessonFactoryState
from app.agents.tools.lesson_port import ModuleBrief

MAX_LESSON_SOURCES = 8  # the best scored, to keep a prompt of reasonable size
LANGUAGES = {"fr": "French", "en": "English"}
# Application instruction, outside the untrusted wrapper: the names of the old APIs (output of the
# Strategist) stay in the sheet, the rule that concerns them is not part of it.
LEGACY_RULE = (
    'Present legacy APIs only in a "Reading older code" callout in the Explanation section. '
    "Use a Markdown blockquote (lines starting with `>`). Explain how to recognize these APIs "
    "in existing code. Recommend current APIs and use those in examples."
)
SOURCE_CHARS = 6000  # text read, handed to the Writer and the Verifier, per source


class Node(Protocol):
    async def __call__(self, state: LessonFactoryState) -> LessonFactoryState: ...


@dataclass(frozen=True)
class LessonSource:
    number: int
    source_id: str
    title: str
    url: str
    score: int
    text: str


def kept_verdicts(state: LessonFactoryState) -> list[dict[str, Any]]:
    """Sources kept by the session (score 60 or more), the best scored first."""
    kept = [v for v in state.get("verdicts", []) if v["verdict"] == "kept"]
    return sorted(kept, key=lambda v: -(v["score"] or 0))  # stable sort: reading order


def lesson_sources(state: LessonFactoryState) -> list[LessonSource]:
    """Lesson sources: kept, read, numbered from 1 to `MAX_LESSON_SOURCES`."""
    pages = {p["source_id"]: p for p in state.get("pages", []) if p.get("source_id")}
    cited = {
        source_url_key(url): number
        for number, url in enumerate(state.get("citation_urls", []), start=1)
    }
    found = [(v, pages[v["source_id"]]) for v in kept_verdicts(state) if v["source_id"] in pages]
    if cited:
        found.sort(key=lambda item: cited.get(source_url_key(item[1]["url"]), len(cited) + 1))
    sources: list[LessonSource] = []
    next_number = len(cited) + 1
    for verdict, page in found[:MAX_LESSON_SOURCES]:
        number = cited.get(source_url_key(page["url"]))
        if number is None:
            number = next_number
            next_number += 1
        sources.append(
            LessonSource(
                number=number,
                source_id=verdict["source_id"],
                title=page_title(page),
                url=page["url"],
                score=verdict["score"],
                text=page["text"][:SOURCE_CHARS],
            )
        )
    return sources


def sources_prompt(sources: list[LessonSource]) -> str:
    """Each source wrapped as untrusted (title, address and text come from the web)."""
    blocks = []
    for source in sources:
        body = f"Title: {one_line(source.title)}\nURL: {source.url}\n\n{source.text}"
        blocks.append(f"[{source.number}]\n{untrusted(body, f'source {source.number}')}")
    return "\n\n".join(blocks)


def module_prompt(brief: ModuleBrief) -> str:
    """The module sheet comes from the program (agent output): wrapped data, not an instruction."""
    lines = [
        f"Title: {brief.title}",
        f"Target skills: {', '.join(brief.skills) or 'unspecified'}",
        f"Prerequisites: {', '.join(brief.prerequisites) or 'none'}",
        f"Week {brief.week_rank}: {brief.week_theme}",
        f"January's goal: {brief.goal_text}",
    ]
    if brief.chapter_context:
        lines.append(brief.chapter_context)
    if brief.legacy:
        lines.append(f"Legacy APIs in this chapter: {', '.join(brief.legacy)}")
    block = untrusted("\n".join(lines), "module")
    return f"{block}\n\n{LEGACY_RULE}" if brief.legacy else block


def brief_of(state: LessonFactoryState) -> ModuleBrief:
    data = state["brief"]
    return ModuleBrief(
        module_id=data["module_id"],
        program_id=data["program_id"],
        title=data["title"],
        skills=tuple(data["skills"]),
        prerequisites=tuple(data["prerequisites"]),
        week_rank=data["week_rank"],
        week_theme=data["week_theme"],
        goal_text=data["goal_text"],
        language=data["language"],
        seed_urls=tuple(data["seed_urls"]),
        chapter_context=data.get("chapter_context", ""),
        legacy=tuple(data.get("legacy", ())),
    )
