from fastapi import FastAPI

from app.db.models.lessons import Lesson
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan

TITLE = "Index et recherche"
OBJECTIVE = "Reconnaître le rôle d’un index."
EXAMPLE = "Une table associe le mot lampe à trois documents."
REFERENCE = "Documentation de l’index"
SOURCE = f"""# {TITLE}

## Objectifs

- {OBJECTIVE}

## L’essentiel

Un index associe des valeurs à des emplacements.

```text
## Ceci reste dans le bloc de code
```

## Explication

On cherche d’abord la clé voulue.

## Exemple travaillé

{EXAMPLE} Voir la [référence][doc].

## Sources

1. [{REFERENCE}][doc]

[doc]: https://example.org/index
"""


async def seed_lesson(app: FastAPI, *, ready: bool = True) -> str:
    factory = app.state.session_factory
    user_id = app.state.local_user_id
    goal = await add_goal(factory, user_id)
    saved = await AgentProgramStore(app.state.program).save_draft(
        user_id,
        f"variantes-{goal.goal_id}",
        goal.goal_id,
        sample_plan().with_chapter_indices(),
        revision=0,
        start_date=MONDAY,
        reason="Préparer plusieurs lectures d’une leçon.",
    )
    async with factory() as db:
        program = await load(db, user_id, saved.program_id)
        program.program.status = "validated"
        lesson = Lesson(
            user_id=user_id,
            module_id=program.modules[0].id,
            program_id=saved.program_id,
            title=TITLE,
            status="ready" if ready else "pending",
            markdown=SOURCE if ready else "",
        )
        db.add(lesson)
        await db.commit()
        return lesson.id
