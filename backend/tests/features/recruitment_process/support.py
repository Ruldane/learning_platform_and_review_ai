from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from app.core.skills import evidence
from app.features.skills.service import SkillsService
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import add_posting
from tests.features.projects.support import Env
from tests.features.study.conftest import seed
from tests.support.gap import analysis_data, requirement

TITLE = "Ingénieure fiabilité des données"
COMPANY = "Labo fictif"
PROJECT = "Audit des délais d’un pipeline"
MISSING = "Justifier la fidélité d’un système RAG"
GRADES = (
    {"marks": [3, 2, 4], "feedback": "Le projet contient des mesures vérifiables."},
    {"marks": [4, 3, 2], "feedback": "La mise en situation fixe un contrôle utile."},
    {"marks": [3, 4, 3], "feedback": "La réponse d’entretien précise une limite."},
)


async def seed_rehearsal(app: FastAPI, user_id: str) -> tuple[str, str]:
    factory = app.state.session_factory
    posting = await add_posting(
        factory,
        user_id,
        title=TITLE,
        company=COMPANY,
        status="ready",
        analysis=analysis_data(
            title=TITLE,
            company=COMPANY,
            requirements=[
                requirement("Traiter des mesures avec Python", True, "Python"),
                requirement(MISSING, True, "RAG"),
            ],
        ),
    )
    program = await seed(app, user_id=user_id, recording=False)
    env = Env(app, user_id, RecordingLauncher(factory), program)
    now = datetime.now(UTC)
    submission = {
        **env.last_submission(),
        "description": "Trente échantillons avec des mesures datées.",
    }
    previous = {
        **submission,
        "description": "Premier essai sans mesures.",
        "at": (now - timedelta(days=1)).isoformat(),
    }
    project = await env.add_project(
        status="validated",
        title=PROJECT,
        submissions=[previous, submission],
        validated_at=now,
        evaluation={
            "at": now.isoformat(),
            "verdict": "validated",
            "results": [],
            "feedback": "Mesures contrôlées.",
            "repo_status": "none",
        },
    )
    async with factory() as db:
        skills = SkillsService(db, user_id)
        await skills.raise_levels(["Python"], "prouve", evidence("project", project, PROJECT, now))
        await db.commit()
    return posting, project
