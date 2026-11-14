"""Matériel des tests du profil maître (D124) : l'app réelle avec un lanceur factice (aucune
session ne tourne, aucun LLM), la vraie mémoire (documents rangés, fichiers relus) et l'extracteur
de mise en page réel mais local ; CV fictifs de `scripts.sample_cv`."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.core.providers import MemoryProviders
from app.db.models.skills import Skill, UserSkill
from app.features.cv.service.runtime import CvRuntime
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.providers.fonts.fake import FakeFontSource
from app.providers.pdf.layout import LocalPdfLayoutExtractor
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import Factory
from tests.support.text_renderer import TextHtmlRenderer

API = "/api/v1"


@pytest.fixture
def launcher_spy(client: httpx.AsyncClient, app: FastAPI) -> RecordingLauncher:
    """Remplace le lanceur du CV, une fois l'app démarrée (`client`)."""
    spy = RecordingLauncher(app.state.session_factory)
    app.state.career.cv.launcher = spy
    return spy


@pytest.fixture
async def memory(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    async with memory_runtime(db_session_factory, memory_providers) as runtime:
        yield runtime


@pytest.fixture
def cv_runtime(
    db_session_factory: Factory, memory: MemoryRuntime, launcher: RecordingLauncher
) -> CvRuntime:
    return CvRuntime(
        db_session_factory,
        memory,
        launcher,
        LocalPdfLayoutExtractor(),
        TextHtmlRenderer(),
        FakeFontSource(),
    )


@pytest.fixture
def launcher(db_session_factory: Factory) -> RecordingLauncher:
    return RecordingLauncher(db_session_factory)


async def skill_rows(factory: Factory, user_id: str) -> dict[str, tuple[str, list[Any]]]:
    """`nom → (niveau, preuves)` des compétences de January."""
    async with factory() as db:
        stmt = select(Skill.name, UserSkill.level, UserSkill.evidence).join(
            UserSkill, UserSkill.skill_id == Skill.id
        )
        rows = (await db.execute(stmt.where(Skill.user_id == user_id))).all()
    return {name: (level, list(evidence)) for name, level, evidence in rows}
