"""Matériel des tests de la feature `quiz` (D101) : l'app réelle (lifespan, vrais runtimes), un
brouillon de programme écrit par le vrai port du Stratège (deux semaines, `sample_plan`), une
leçon prête au premier module, une en attente au second, un lanceur factice (aucune session
réelle, aucun LLM) et une horloge figée (mardi 17/11, Paris). Aucun réseau."""

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.plan_schema import PlanDraft
from app.db.models.lessons import Lesson
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from app.features.quiz.service.runtime import QuizRuntime
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import MONDAY, add_goal, sample_plan

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)  # mardi de la semaine 1, 11 h à Paris
SKILLS = ["pandas", "Séries", "Index"]
LESSON = "# Module Bases\n\nLes séries et les index de pandas."


@dataclass
class Seeded:
    app: FastAPI
    user_id: str
    program_id: str
    modules: list[str]  # par semaine puis rang
    launcher: RecordingLauncher

    @property
    def rt(self) -> QuizRuntime:
        runtime: QuizRuntime = self.app.state.quiz
        return runtime

    def at(self, moment: datetime) -> None:
        """Fige l'horloge des quiz à `moment`."""
        self.rt.now = lambda: moment


def three_skill_plan() -> PlanDraft:
    """`sample_plan`, le premier module couvrant trois compétences."""
    plan = sample_plan()
    plan.weeks[0].modules[0].skills = list(SKILLS)
    return plan


async def seed(
    app: FastAPI, plan: PlanDraft | None = None, ready: int = 1, user_id: str | None = None
) -> Seeded:
    """Brouillon (sans validation : rien n'est lancé) ; leçons prêtes aux `ready` premiers
    modules, en attente aux autres."""
    user = user_id or app.state.local_user_id
    factory = app.state.session_factory
    rows = await add_goal(factory, user)
    saved = await AgentProgramStore(app.state.program).save_draft(
        user, "s-draft", rows.goal_id, plan or three_skill_plan(), revision=0,
        start_date=MONDAY, reason="v1",
    )  # fmt: skip
    async with factory() as db:
        modules = [m for m in (await load(db, user, saved.program_id)).modules if not m.skipped]
        for index, module in enumerate(modules):
            status = "ready" if index < ready else "pending"
            db.add(
                Lesson(
                    user_id=user,
                    module_id=module.id,
                    program_id=saved.program_id,
                    title=module.title,
                    markdown=LESSON if status == "ready" else "",
                    status=status,
                )
            )
        await db.commit()
    launcher = RecordingLauncher(factory)
    app.state.quiz.launcher = launcher
    app.state.quiz.now = lambda: NOW
    return Seeded(app, user, saved.program_id, [m.id for m in modules], launcher)


@pytest.fixture
async def seeded(client: httpx.AsyncClient, app: FastAPI) -> Seeded:
    return await seed(app)
