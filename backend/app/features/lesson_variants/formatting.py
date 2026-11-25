import unicodedata
from dataclasses import dataclass

from markdown_it import MarkdownIt

_MARKDOWN = MarkdownIt("commonmark")


@dataclass(frozen=True)
class Section:
    start: int
    title: str


def _sections(markdown: str) -> list[Section]:
    tokens = _MARKDOWN.parse(markdown)
    sections: list[Section] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0 and token.map:
            sections.append(Section(token.map[0], tokens[index + 1].content))
    return sections


def _priority(title: str) -> int:
    folded = "".join(
        char
        for char in unicodedata.normalize("NFKD", title.casefold())
        if not unicodedata.combining(char)
    )
    if folded.startswith("objectif"):
        return 0
    if folded.startswith("exemple"):
        return 1
    return 2


def prepare_formats(markdown: str) -> tuple[str, list[str]]:
    """The sheet puts objectives and examples first. The reading follows the published order."""
    sections = _sections(markdown)
    if not sections:
        return markdown, []
    lines = markdown.splitlines(keepends=True)
    blocks = []
    for index, section in enumerate(sections):
        end = sections[index + 1].start if index + 1 < len(sections) else len(lines)
        blocks.append((_priority(section.title), "".join(lines[section.start : end])))
    preamble = "".join(lines[: sections[0].start])
    ordered = [preamble, *(body for _, body in sorted(blocks, key=lambda block: block[0]))]
    return "\n\n".join(block.rstrip("\r\n") for block in ordered if block), [
        section.title for section in sections
    ]
