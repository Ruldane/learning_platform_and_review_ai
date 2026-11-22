import re
from hashlib import sha256
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.lessons.service.lessons import get_lesson

_MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
_BLOCK_END = {
    "blockquote",
    "br",
    "dd",
    "dt",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "p",
    "pre",
    "td",
    "th",
}
MAX_LESSON_CONTEXT = 2_800
PASSAGE_MARGIN = 700
_TITLE = re.compile(r"^ {0,3}#[ \t]+\S")
_SECTION = re.compile(r"^ {0,3}#{2,6}[ \t]")
_FENCE = re.compile(r"^ {0,3}(```|~~~)")


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "hr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_END:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


async def ready_lesson(db: AsyncSession, user_id: str, lesson_id: str) -> tuple[str, str]:
    lesson = await get_lesson(db, user_id, lesson_id)
    if lesson.status != "ready":
        raise AppError("lesson_not_ready", "Cette leçon n'est pas encore prête.", 409)
    return lesson.title, lesson.markdown


def lesson_version(markdown: str) -> str:
    return sha256(markdown.encode()).hexdigest()


def stale_passage() -> AppError:
    return AppError(
        "conversation_passage_stale",
        "Ce passage a changé. Sélectionne de nouveau le texte dans la leçon.",
        409,
    )


def _without_leading_title(markdown: str) -> str:
    """Le lecteur affiche séparément le premier titre de niveau 1 avant toute section."""
    lines = markdown.split("\n")
    fence = False
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            fence = not fence
        if fence:
            continue
        if _SECTION.match(line):
            break
        if _TITLE.match(line):
            lines[index] = ""
            return "\n".join(lines)
    return markdown


def lesson_material(markdown: str, passage: str | None, occurrence: int | None) -> str:
    """Relit le texte sélectionnable, y compris autour d'un passage éloigné du début."""
    parser = _VisibleText()
    parser.feed(_MARKDOWN.render(_without_leading_title(markdown)))
    parser.close()
    text = "".join(parser.parts).strip()
    if passage is None:
        return text[:MAX_LESSON_CONTEXT]
    flat = " ".join(text.split())
    matches = re.finditer(re.escape(passage), flat)
    if occurrence is not None:
        selected = next((match for index, match in enumerate(matches) if index == occurrence), None)
    else:
        selected = next(matches, None)
        if next(matches, None) is not None:
            raise AppError(
                "conversation_passage_ambiguous",
                "Ce passage apparaît plusieurs fois dans la leçon. Indique l’occurrence voulue.",
                409,
            )
    if selected is None:
        raise stale_passage()
    return flat[max(0, selected.start() - PASSAGE_MARGIN) : selected.end() + PASSAGE_MARGIN]
