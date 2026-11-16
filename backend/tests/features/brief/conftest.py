"""Matériel des tests du brief (D162) : l'app réelle (lifespan, vrais runtimes), un lanceur qui
écrit la session `running` sans faire tourner de graphe, et une horloge figée au mardi 17 novembre
2026, 11 h à Paris (l'heure du brief, 7 h, est passée) sur le brief, les quiz, l'étude et les
candidatures. Aucun réseau ni LLM."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.features.brief.service.runtime import BriefRuntime
from tests.features.lessons.conftest import RecordingLauncher

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)  # mardi 11 h à Paris ; brief réglé à 7 h
TODAY = date(2026, 11, 17)
OTHER = "autre-utilisatrice"


@dataclass
class Env:
    app: FastAPI
    user_id: str
    launcher: RecordingLauncher

    @property
    def rt(self) -> BriefRuntime:
        runtime: BriefRuntime = self.app.state.daily.brief
        return runtime

    def at(self, moment: datetime) -> None:
        """Fige l'horloge du brief et des features dont il lit les faits."""
        for runtime in (self.rt, self.rt.quiz, self.rt.study, self.rt.applications):
            runtime.now = lambda: moment


@pytest.fixture
def env(client: httpx.AsyncClient, app: FastAPI) -> Env:
    launcher = RecordingLauncher(app.state.session_factory)
    app.state.daily.brief.launcher = launcher
    found = Env(app, app.state.local_user_id, launcher)
    found.at(NOW)
    return found


@pytest.fixture
def rt(env: Env) -> BriefRuntime:
    return env.rt
