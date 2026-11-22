"""Contexte pédagogique d'un chapitre à partir de la table des matières."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.db.models.program import Module
from app.features.lessons.service.lessons import ready_markdown
from app.features.lessons.service.sections import lesson_parts
from app.features.program.service.chapters import ProgramOutline, program_outline
from app.features.program.service.programs import Loaded

SUMMARY_CHARS = 1_200


async def _previous_summary(
    db: AsyncSession, user_id: str, loaded: Loaded, outline: ProgramOutline, index: int
) -> str:
    for module in loaded.modules:
        if outline.chapter_indices.get(module.id) != index:
            continue
        if markdown := await ready_markdown(db, user_id, module.id):
            sections = lesson_parts(markdown).sections
            if sections:
                return sections[0][1][:SUMMARY_CHARS]
    return ""


async def chapter_context(db: AsyncSession, user_id: str, loaded: Loaded, module: Module) -> str:
    outline = await program_outline(db, user_id, loaded.program.id)
    chapters = outline.chapters
    index = outline.chapter_indices.get(module.id)
    if index is None or not 0 <= index < len(chapters):
        return ""
    current = chapters[index]
    names = {normalize_skill_name(name) for name in current.requires}
    earlier = [notion for chapter in chapters[:index] for notion in chapter.introduces]
    lines = ["Notions requises du glossaire"]
    lines.extend(
        f"- {notion.name} : {notion.definition}"
        for notion in earlier
        if normalize_skill_name(notion.name) in names
    )
    lines.append("Notions à introduire")
    lines.extend(f"- {notion.name} : {notion.definition}" for notion in current.introduces)
    if index:
        previous = chapters[index - 1].title
        lines.append(f"Chapitre précédent : {previous}")
        if summary := await _previous_summary(db, user_id, loaded, outline, index - 1):
            lines.append(summary)
    if index + 1 < len(chapters):
        following = chapters[index + 1]
        lines.append(f"Chapitre suivant : {following.title}")
        if following.introduces:
            following_names = ", ".join(notion.name for notion in following.introduces)
            lines.append(f"Notions prévues ensuite : {following_names}")
    return "\n".join(lines)
