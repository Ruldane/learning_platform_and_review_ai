"""Fixtures des tests des projets (D166) : l'app réelle, un programme validé de deux semaines
(deux modules : « Module Bases » et « Module Projet »), un lanceur factice et l'horloge figée au
mardi 24/11 (les deux semaines ont commencé)."""

import httpx
import pytest
from fastapi import FastAPI

from app.features.projects.service.runtime import ProjectsRuntime
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.projects.support import NOW, Env
from tests.features.study.conftest import seed
from tests.support.direct import drafted  # noqa: F401


@pytest.fixture
async def env(client: httpx.AsyncClient, app: FastAPI) -> Env:
    seeded = await seed(app)
    launcher = RecordingLauncher(app.state.session_factory)
    app.state.daily.projects.launcher = launcher
    found = Env(app, seeded.user_id, launcher, seeded)
    found.at(NOW)
    return found


@pytest.fixture
def rt(env: Env) -> ProjectsRuntime:
    return env.rt
