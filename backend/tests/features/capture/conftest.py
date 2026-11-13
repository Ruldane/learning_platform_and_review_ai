"""Matériel des tests de la feature `capture` (D108) : la vraie base de test, la vraie mémoire
(`HashingEmbedder`, Qdrant en mémoire), le vrai programme (validé sans production des leçons),
le vrai port de la capture, un lanceur factice (aucune session réelle, aucun LLM) et une horloge
figée (mercredi 18/11, 10 h à Paris)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest

from app.core.providers import MemoryProviders
from app.features.capture.service.runtime import CaptureRuntime
from app.features.capture.service.store import AgentCaptureStore
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.program.service.runtime import ProgramRuntime
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import Factory
from tests.features.replan.conftest import NOW


@dataclass
class Capture:
    rt: CaptureRuntime
    store: AgentCaptureStore
    memory: MemoryRuntime
    program: ProgramRuntime
    launcher: RecordingLauncher


@pytest.fixture
async def capture(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> AsyncIterator[Capture]:
    async with memory_runtime(db_session_factory, memory_providers) as memory:
        program = ProgramRuntime(db_session_factory, memory)
        launcher = RecordingLauncher(db_session_factory)
        rt = CaptureRuntime(db_session_factory, launcher, program, memory, now=lambda: NOW)
        yield Capture(rt, AgentCaptureStore(rt), memory, program, launcher)
