"""Matériel des tests de la feature `study` (D103) : l'app réelle (lifespan, vrais runtimes), un
programme validé de deux semaines écrit par le vrai port du Stratège, des leçons prêtes (leçon
3.5 complète de `lesson_markdown`), des tâches datées autour de mardi 17/11 (Paris) et une
horloge figée. Le lanceur est factice (aucune session réelle) sauf pour les tests qui montent le
parcours `study_session` de test (`stub.py`). Aucun réseau ni LLM."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update

from app.db.models.lessons import Lesson
from app.db.models.program import Program, Task
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from app.features.study.service.runtime import StudyRuntime
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import MONDAY, add_goal, sample_plan
from tests.features.study.stub import StubControl, install
from tests.support.lessons import lesson_markdown

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)  # mardi de la semaine 1, 11 h à Paris
TUESDAY = date(2026, 11, 17)
SKILLS = ["pandas", "Séries", "Index"]
LESSON_WORDS = 400
# Dates des tâches du premier module : une lecture en retard (lundi), une due (mardi), les
# autres plus tard ; pratique et quiz dus mardi.
DATES = {
    "Lire le chapitre 1": MONDAY,
    "Lire le chapitre 2": TUESDAY,
    "Lire le chapitre 3": TUESDAY + timedelta(days=1),
    "Lire le chapitre 4": TUESDAY + timedelta(days=2),
    "Lire le chapitre 5": TUESDAY + timedelta(days=3),
    "Pratiquer les bases": TUESDAY,
    "Faire le quiz 1": TUESDAY,
}
# Bloc du mardi : le retard d'abord, puis l'ordre du programme (rang), sans le quiz.
BLOCK = ["Lire le chapitre 1", "Pratiquer les bases", "Lire le chapitre 2"]


@dataclass
class Seeded:
    app: FastAPI
    user_id: str
    program_id: str
    modules: list[str]  # par semaine puis rang
    lessons: list[str]  # leçon de chaque module
    tasks: dict[str, str]  # titre → id
    launcher: RecordingLauncher | None

    @property
    def rt(self) -> StudyRuntime:
        runtime: StudyRuntime = self.app.state.study
        return runtime

    def at(self, moment: datetime) -> None:
        """Fige l'horloge de l'étude à `moment`."""
        self.rt.now = lambda: moment


async def seed(
    app: FastAPI,
    *,
    ready: tuple[bool, bool] = (True, True),
    user_id: str | None = None,
    recording: bool = True,
    validated: bool = True,
) -> Seeded:
    user = user_id or app.state.local_user_id
    factory = app.state.session_factory
    plan = sample_plan()
    plan.weeks[0].modules[0].skills = list(SKILLS)
    rows = await add_goal(factory, user)
    saved = await AgentProgramStore(app.state.program).save_draft(
        user, "s-draft", rows.goal_id, plan, revision=0, start_date=MONDAY, reason="v1"
    )
    async with factory() as db:
        if validated:
            await db.execute(
                update(Program).where(Program.id == saved.program_id).values(status="validated")
            )
        modules = [m for m in (await load(db, user, saved.program_id)).modules if not m.skipped]
        lessons: list[str] = []
        for module, is_ready in zip(modules, ready, strict=True):
            lesson = Lesson(
                user_id=user,
                module_id=module.id,
                program_id=saved.program_id,
                title=f"Leçon {module.title}",
                markdown=lesson_markdown(LESSON_WORDS) if is_ready else "",
                status="ready" if is_ready else "pending",
            )
            db.add(lesson)
            await db.flush()
            lessons.append(lesson.id)
        for title, day in DATES.items():
            await db.execute(
                update(Task)
                .where(Task.program_id == saved.program_id, Task.title == title)
                .values(planned_date=day)
            )
        found = await db.execute(select(Task.title, Task.id).where(Task.user_id == user))
        tasks = {title: task_id for title, task_id in found.all()}
        await db.commit()
    launcher = RecordingLauncher(factory) if recording else None
    runtime: StudyRuntime = app.state.study
    if launcher is not None:
        runtime.launcher = launcher
    runtime.now = lambda: NOW
    return Seeded(app, user, saved.program_id, [m.id for m in modules], lessons, tasks, launcher)


@pytest.fixture
async def seeded(client: httpx.AsyncClient, app: FastAPI) -> Seeded:
    return await seed(app)


@pytest.fixture
def stub_tutor(monkeypatch: pytest.MonkeyPatch) -> Iterator[StubControl]:
    control = install(monkeypatch)
    yield control
    if control.hold is not None:
        control.hold.set()


@pytest.fixture
async def tutored(stub_tutor: StubControl, client: httpx.AsyncClient, app: FastAPI) -> Seeded:
    """Programme semé, vrai lanceur lié au vrai moteur, parcours `study_session` de test."""
    return await seed(app, recording=False)
