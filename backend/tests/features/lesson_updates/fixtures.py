"""Leçon et journaux de versions fictifs pour la régression et la recette."""

import json

from fastapi import FastAPI
from sqlalchemy import select

from app.core.lesson_structure import LEGACY_SECTIONS, SECTIONS
from app.db.base import utcnow
from app.db.models.lessons import Lesson
from app.db.models.reading_stack import ReadingItem
from tests.agents.graphs.council_models import URLS
from tests.features.lessons.test_router import Seeded, seed
from tests.support.lessons import lesson_markdown

TITLE = "Module Bases"
BEFORE = "import fictilib as lib\n\nresult = lib.old_api([1, 2])"
AFTER = "import fictilib as lib\n\nresult = lib.new_api([1, 2])"
UNCHANGED = 'message = "fictilib.unused_api"'
RELEASE = URLS[0]
VERSION = "2.0.0"
RELEASE_TEXT = (
    "Removed `fictilib.old_api`; use `fictilib.new_api`.\n"
    "Removed `fictilib.unused_api`; use `fictilib.other_api`."
)
CORRECTION = json.dumps(
    {
        "explanation": "La version 2.0.0 renomme la fonction en conservant son rôle.",
        "replacements": [{"block": 1, "code": AFTER}],
    }
)
MARKER = "Preparing a version fix"


async def seed_update(app: FastAPI, *, legacy: bool = False) -> Seeded:
    seeded = await seed(app)
    owner: str = app.state.local_user_id
    markdown = lesson_markdown(title=TITLE, urls=(RELEASE, URLS[1])).replace(
        "## Worked example\n",
        f"## Worked example\n\n```python\n{BEFORE}\n```\n\n```python\n{UNCHANGED}\n```\n",
    )
    if legacy:
        for current, previous in zip(SECTIONS, LEGACY_SECTIONS, strict=True):
            markdown = markdown.replace(f"\n## {current}\n", f"\n## {previous}\n", 1)
    async with app.state.session_factory() as db:
        lesson = await db.scalar(select(Lesson).where(Lesson.id == seeded.lesson_id))
        assert lesson is not None
        lesson.markdown = markdown
        for url in (RELEASE, RELEASE + "?mirror=1"):
            db.add(
                ReadingItem(
                    user_id=owner,
                    kind="release",
                    url=url,
                    title=f"fictilib {VERSION}",
                    summary="La version modifie deux appels.",
                    text=RELEASE_TEXT,
                    reason="Veille de bibliothèque",
                    created_at=utcnow(),
                )
            )
        await db.commit()
    return seeded
