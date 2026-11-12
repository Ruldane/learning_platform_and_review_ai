"""Composition du moteur d'agents (partie de `app.bootstrap`, qui la réexporte) : réglages lus
par le moteur, ports adaptés des features (D82), production des leçons et contexte des tâches
planifiées (D91). Comme `app.bootstrap`, seul `app.main` (par `app.bootstrap`) l'importe
(contrat 5)."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.tools.memory_port import MemoryGateway
from app.agents.tools.web_port import WebGateway
from app.core.providers import MemoryProviders, PublishingProviders
from app.features.learning.service.runtime import LearningRuntime
from app.features.learning.service.store import AgentCouncilStore
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.store import AgentLessonStore
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.service import SettingsRunReader
from app.scheduler.base import JobContext


def run_settings_source(session_factory: async_sessionmaker[AsyncSession]) -> RunSettingsSource:
    """Réglages lus par le moteur d'agents, adaptés du service de la feature `settings` : le
    moteur n'importe aucune feature (contrat 6)."""
    return SettingsRunReader(session_factory)


def memory_gateway(runtime: MemoryRuntime) -> MemoryGateway:
    """Mémoire vue par le moteur d'agents (outils `memory_*`, Archiviste), adaptée du service de la
    feature `memory` : le moteur n'importe aucune feature (contrat 6, D68)."""
    return AgentMemoryGateway(runtime)


def web_gateway(runtime: ResearchRuntime) -> WebGateway:
    """Recherche web vue par le moteur d'agents (outils `web_*`, Éclaireur), adaptée du service de
    la feature `research` : le moteur n'importe aucune feature (contrat 6, D77)."""
    return AgentWebGateway(runtime)


def agent_ports(
    memory: MemoryRuntime,
    research: ResearchRuntime,
    *,
    learning: LearningRuntime,
    program: ProgramRuntime,
    lessons: LessonsRuntime,
) -> AgentPorts:
    """Tous les ports du moteur (D82) : un port de plus = un champ d'`AgentPorts` et une ligne ici.
    Conseil (D84), programme (D86) et leçons (D90) adaptés des features `learning` (D87),
    `program` (D88) et `lessons` (D91)."""
    council = AgentCouncilStore(learning.session_factory, learning.launcher, learning)
    program_store = AgentProgramStore(program)
    return AgentPorts(
        memory_gateway(memory),
        web_gateway(research),
        council,
        program_store,
        AgentLessonStore(lessons),
    )


def lessons_runtime(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    memory: MemoryRuntime,
    research: ResearchRuntime,
    files: MemoryProviders,
    publishing: PublishingProviders,
) -> LessonsRuntime:
    """Production des leçons (D91) : lanceur (lié au moteur ensuite), mémoire (leçon rangée),
    recherche (copies des PDF), stockage des fichiers de la mémoire, rendu PDF de nos gabarits."""
    return LessonsRuntime(session_factory, launcher, memory, research, files.storage, publishing)


def scheduler_context(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    lessons: LessonsRuntime,
) -> JobContext:
    """Ce que reçoivent les tâches planifiées (D91) : base, lanceur, production des leçons."""
    return JobContext(session_factory, launcher, lessons)
