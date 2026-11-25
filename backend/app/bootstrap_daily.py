"""Daily wiring (phase 8, D160): radar readings, the day's brief and projects. Kept out of
`app.main` (300 lines): one more feature = one field of `DailyRuntimes` and one line in
`daily_runtimes`. As with `app.bootstrap`, only `app.main` imports it (contract 5)."""

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
    """What the daily routes read from `app.state.daily`, what the scheduled tasks receive
    (`JobContext.daily`) and the ports they give to the engine (`agent_ports`)."""

    radar: RadarRuntime  # readings, Monday task, market request (D160)
    radar_store: RadarStore  # `market_radar` flow port (D159)
    brief: BriefRuntime  # day's brief, morning task (D162)
    brief_store: BriefStore  # `daily_brief` flow port (D161, D162)
    projects: ProjectsRuntime  # mini projects, statement task, profile entry (D166)
    project_store: ProjectStore  # port of the `project_brief` and `project_review` flows (D165)
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
    """Radar (base, launcher linked to the engine later, reading of pages through web search) and
    its port; day's brief (quizzes, study and applications whose facts it reads) and its port.
    `career` and `study`: the projects also read memory, file storage and the master profile
    of `career.cv` (stored captures, level reflection, project entry)."""
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
