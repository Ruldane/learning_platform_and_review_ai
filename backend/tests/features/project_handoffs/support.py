from uuid import uuid4

from fastapi import FastAPI

from app.db.models.daily import Project

TITLE = "Catalogue de la bibliothèque"
SUBMISSION = "Le rendu synthétique garde la liste des livres et son filtre."
DATE = "2025-04-05T11:00:00+00:00"


async def seed_project(app: FastAPI, *, submitted: bool = True) -> str:
    async with app.state.session_factory() as db:
        project = Project(
            user_id=app.state.local_user_id,
            program_id=str(uuid4()),
            module_id=str(uuid4()),
            title=TITLE,
            status="validated" if submitted else "todo",
            submissions=(
                [{"at": DATE, "description": SUBMISSION, "repo_url": None, "screenshots": []}]
                if submitted
                else []
            ),
        )
        db.add(project)
        await db.commit()
        return project.id


async def submit_new_version(app: FastAPI, project_id: str) -> None:
    async with app.state.session_factory() as db:
        project = await db.get(Project, project_id)
        assert project is not None
        project.submissions = [
            *project.submissions,
            {
                "at": "2025-05-06T11:00:00+00:00",
                "description": "Une nouvelle version du catalogue est disponible.",
                "repo_url": None,
                "screenshots": [],
            },
        ]
        await db.commit()
