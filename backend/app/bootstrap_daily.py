"""Composition du quotidien (phase 8, D160) : relevé du radar, brief du jour et projets. Gardée
hors de `app.main` (300 lignes) : une feature de plus = un champ de `DailyRuntimes` et une ligne
dans `daily_runtimes`. Comme `app.bootstrap`, seul `app.main` l'importe (contrat 5)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.brief_port import BriefStore
from app.agents.tools.podcast_port import PodcastStore
from app.agents.tools.project_port import ProjectStore
from app.agents.tools.radar_port import RadarStore
from app.bootstrap_agents import StudyRuntimes
from app.bootstrap_career import CareerRuntimes
from app.features.brief.service.runtime import BriefRuntime
from app.features.brief.service.store import AgentBriefStore
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.podcast.service.store import AgentPodcastStore
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.store import AgentProjectStore
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.store import AgentRadarStore
from app.features.research.service.runtime import ResearchRuntime
from app.providers.github.base import GithubContributions
from app.providers.speech.realtime import OpenAIRealtimeSpeech


@dataclass(frozen=True)
class DailyRuntimes:
    """Ce que les routes du quotidien lisent sur `app.state.daily`, ce que les tâches planifiées
    reçoivent (`JobContext.daily`) et les ports qu'elles donnent au moteur (`agent_ports`)."""

    radar: RadarRuntime  # relevés, tâche du lundi, demande du marché (D160)
    radar_store: RadarStore  # port du parcours `market_radar` (D159)
    brief: BriefRuntime  # brief du jour, tâche du matin (D162)
    brief_store: BriefStore  # port du parcours `daily_brief` (D161, D162)
    projects: ProjectsRuntime  # mini projets, tâche des énoncés, entrée au profil (D166)
    project_store: ProjectStore  # port des parcours `project_brief` et `project_review` (D165)
    podcast: PodcastRuntime
    podcast_store: PodcastStore


def daily_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    research: ResearchRuntime,
    career: CareerRuntimes,
    study: StudyRuntimes,
    github: GithubContributions,
) -> DailyRuntimes:
    """Radar (base, lanceur lié au moteur ensuite, lecture des pages par la recherche web) et son
    port ; brief du jour (quiz, étude et candidatures dont il lit les faits) et son port. `career`
    et `study` : les projets lisent aussi la mémoire, le stockage des fichiers et le profil maître
    de `career.cv` (captures rangées, reflet des niveaux, entrée de projet)."""
    radar = RadarRuntime(session_factory, launcher, research)
    brief = BriefRuntime(session_factory, launcher, study.quiz, study.study, career.applications)
    cv = career.cv
    projects = ProjectsRuntime(
        session_factory, launcher, cv.storage, cv.memory, cv, research, github
    )
    podcast = PodcastRuntime(
        session_factory, launcher, study.quiz, cv.storage, OpenAIRealtimeSpeech(research.keys)
    )
    return DailyRuntimes(
        radar=radar,
        radar_store=AgentRadarStore(radar),
        brief=brief,
        brief_store=AgentBriefStore(brief),
        projects=projects,
        project_store=AgentProjectStore(projects),
        podcast=podcast,
        podcast_store=AgentPodcastStore(podcast),
    )
