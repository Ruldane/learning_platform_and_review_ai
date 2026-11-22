from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from tests.features.lessons.conftest import RecordingLauncher
from tests.features.projects.support import Env
from tests.features.study.conftest import seed
from tests.support.projects import sample_brief

TITLE = "Journal de mesures"
CRITERION = "Rendre le prélèvement reproductible"
ORIGINAL = "La première lecture ne retrouve pas les dates dans le relevé."
SECOND = "La seconde lecture confirme que le relevé décrit les dates et le protocole."
DESCRIPTION = "Le protocole fixe trois lectures par jour et date les mesures du 12 au 18 avril."
REASON = "Les dates se trouvent dans le dernier paragraphe de la remise."


async def seed_reviewed_project(app: FastAPI, user_id: str) -> str:
    program = await seed(app, user_id=user_id, recording=False)
    env = Env(app, user_id, RecordingLauncher(app.state.session_factory), program)
    now = datetime.now(UTC)
    submission = {**env.last_submission(), "description": DESCRIPTION, "repo_url": None}
    previous = {
        **submission,
        "description": "Le premier relevé ne contient aucune mesure datée.",
        "at": (now - timedelta(days=1)).isoformat(),
    }
    return await env.add_project(
        status="to_redo",
        title=TITLE,
        brief={**sample_brief().model_dump(mode="json"), "criteria": [CRITERION]},
        submissions=[previous, submission],
        evaluation={
            "at": now.isoformat(),
            "verdict": "to_redo",
            "results": [{"index": 1, "met": False, "comment": ORIGINAL}],
            "feedback": ORIGINAL,
            "repo_status": "none",
        },
    )
