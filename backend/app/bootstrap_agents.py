"""Composition du moteur d'agents (partie de `app.bootstrap`, qui la réexporte) : réglages lus
par le moteur, ports adaptés des features (D82), production des leçons et contexte des tâches
planifiées (D91). Comme `app.bootstrap`, seul `app.main` (par `app.bootstrap`) l'importe
(contrat 5)."""

from dataclasses import dataclass

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
from app.features.quiz.service.runtime import QuizRuntime
from app.features.quiz.service.store import AgentQuizStore
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.service import SettingsRunReader
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.store import AgentStudyStore
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


@dataclass(frozen=True)
class StudyRuntimes:
    """Les features de l'étude (phase 5), créées ensemble pour garder `app.main` court (F23) :
    une feature de plus = un champ ici, une ligne dans `study_runtimes` et dans `agent_ports`."""

    quiz: QuizRuntime
    study: StudyRuntime


def study_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    program: ProgramRuntime,
    memory: MemoryRuntime,
) -> StudyRuntimes:
    """Quiz et révisions (D101), sessions guidées (D103) : lanceur (lié au moteur ensuite),
    programme (verrou, tâches cochées ou de suivi), mémoire (reflet des niveaux)."""
    return StudyRuntimes(
        quiz=QuizRuntime(session_factory, launcher, program, memory),
        study=StudyRuntime(session_factory, launcher, program, memory),
    )


def agent_ports(
    memory: MemoryRuntime,
    research: ResearchRuntime,
    *,
    learning: LearningRuntime,
    program: ProgramRuntime,
    lessons: LessonsRuntime,
    study: StudyRuntimes,
) -> AgentPorts:
    """Tous les ports du moteur (D82) : un port de plus = un champ d'`AgentPorts` et une ligne ici.
    Conseil (D84), programme (D86), leçons (D90), quiz (D100) et sessions d'étude (D102)
    adaptés des features `learning` (D87), `program` (D88), `lessons` (D91), `quiz` (D101) et
    `study` (D103)."""
    council = AgentCouncilStore(learning.session_factory, learning.launcher, learning)
    program_store = AgentProgramStore(program)
    return AgentPorts(
        memory_gateway(memory),
        web_gateway(research),
        council,
        program_store,
        AgentLessonStore(lessons),
        AgentQuizStore(study.quiz),
        AgentStudyStore(study.study),
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
