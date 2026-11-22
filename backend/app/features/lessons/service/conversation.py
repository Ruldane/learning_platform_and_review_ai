import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.lessons.repository import LessonRepository

# Les mots pédagogiques courants ne pointent vers aucun chapitre en particulier.
_STOP = frozenset(
    [
        "avec",
        "cette",
        "comme",
        "comment",
        "dans",
        "des",
        "dire",
        "elle",
        "encore",
        "entre",
        "est",
        "faire",
        "faut",
        "fois",
        "leur",
        "les",
        "même",
        "module",
        "peux",
        "peux-tu",
        "plus",
        "pourquoi",
        "pour",
        "que",
        "quel",
        "quelle",
        "quelles",
        "quels",
        "qui",
        "quoi",
        "sans",
        "ses",
        "sont",
        "suis",
        "sur",
        "tes",
        "ton",
        "tous",
        "tout",
        "très",
        "une",
        "veux",
        "voudrais",
    ]
)
MAX_TERMS = 10
MAX_LESSONS = 3


@dataclass(frozen=True)
class PublishedReference:
    id: str
    title: str
    markdown: str


def lesson_terms(text: str) -> list[str]:
    words = re.findall(r"[^\W\d_]{3,}", text.lower())
    return list(dict.fromkeys(word for word in words if word not in _STOP))[:MAX_TERMS]


async def search_published(
    db: AsyncSession,
    user_id: str,
    terms: list[str],
    previous: list[str],
    *,
    followed_only: bool = False,
) -> list[PublishedReference]:
    found = await LessonRepository(db, user_id).ready_for_conversation(
        terms,
        previous,
        MAX_LESSONS,
        followed_only=followed_only,
    )
    return [PublishedReference(lesson.id, lesson.title, lesson.markdown) for lesson in found]
