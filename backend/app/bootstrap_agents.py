"""Agent engine wiring (part of `app.bootstrap`, which re-exports it): settings read by the
engine, ports adapted from the features (D82), lesson production and context for scheduled
tasks (D91). As with `app.bootstrap`, only `app.main` (via `app.bootstrap`) imports it
(contract 5)."""

from dataclasses import dataclass, replace

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.tools.applications_port import NO_APPLICATIONS, ApplicationStore
from app.agents.tools.boss_port import NO_BOSS, BossReviewPort
from app.agents.tools.brief_port import NO_BRIEF, BriefStore
from app.agents.tools.committee_port import NO_COMMITTEE, CommitteeStore
from app.agents.tools.cv_review_port import NO_CV_REVIEW, CvReviewStore
from app.agents.tools.cv_template_port import NO_CV_TEMPLATES, CvTemplateStore
from app.agents.tools.gap_port import NO_GAP, GapStore
from app.agents.tools.ide_port import NO_IDE, IdeStore
from app.agents.tools.interview_port import NO_INTERVIEWS, InterviewStore
from app.agents.tools.kit_port import NO_KIT, KitStore
from app.agents.tools.memory_port import MemoryGateway
from app.agents.tools.podcast_port import NO_PODCAST, PodcastStore
from app.agents.tools.profile_port import NO_PROFILE, ProfileStore
from app.agents.tools.project_port import NO_PROJECTS, ProjectStore
from app.agents.tools.radar_port import NO_RADAR, RadarStore
from app.agents.tools.web_port import WebGateway
from app.core.providers import MemoryProviders, PublishingProviders
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.blind_assessment.service.store import AgentBlindAssessmentStore
from app.features.book.service.runtime import BookRuntime
from app.features.capture.service.runtime import CaptureRuntime
from app.features.capture.service.store import AgentCaptureStore
from app.features.code_trial.store import AgentCodeTrialStore
from app.features.conversations.store import AgentConversationStore
from app.features.expert_debates.service import AgentExpertDebates
from app.features.grade_appeals.service.store import AgentGradeAppealsStore
from app.features.learning.service.runtime import LearningRuntime
from app.features.learning.service.store import AgentCouncilStore
from app.features.lesson_hunt.service.store import AgentLessonHuntStore
from app.features.lesson_updates.service.store import AgentLessonUpdatesStore
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.store import AgentLessonStore
from app.features.linkedin_drafts.service.store import AgentLinkedInStore
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime
from app.features.oncall.service.report import AgentOncallStore
from app.features.paper_lab.service.store import AgentPaperLabStore
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from app.features.quiz.service.runtime import QuizRuntime
from app.features.quiz.service.store import AgentQuizStore
from app.features.recruitment_process.service.store import AgentRecruitmentStore
from app.features.replan.service.runtime import ReplanRuntime
from app.features.replan.service.store import AgentReplanStore
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.service import SettingsRunReader
from app.features.skill_transfer.service.store import AgentSkillTransferStore
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.store import AgentStudyStore
from app.scheduler.base import DailyJobs, JobContext


def run_settings_source(session_factory: async_sessionmaker[AsyncSession]) -> RunSettingsSource:
    """Settings read by the agent engine, adapted from the `settings` feature service: the
    engine imports no feature (contract 6)."""
    return SettingsRunReader(session_factory)


def memory_gateway(runtime: MemoryRuntime) -> MemoryGateway:
    """Memory as seen by the agent engine (`memory_*` tools, Archivist), adapted from the `memory`
    feature service: the engine imports no feature (contract 6, D68)."""
    return AgentMemoryGateway(runtime)


def web_gateway(runtime: ResearchRuntime) -> WebGateway:
    """Web search as seen by the agent engine (`web_*` tools, Scout), adapted from the `research`
    feature service: the engine imports no feature (contract 6, D77)."""
    return AgentWebGateway(runtime)


@dataclass(frozen=True)
class StudyRuntimes:
    """The study features (phase 5), created together to keep `app.main` short (F23):
    one more feature = one field here, one line in `study_runtimes` and in `agent_ports`."""

    quiz: QuizRuntime
    study: StudyRuntime
    replan: ReplanRuntime
    capture: CaptureRuntime


def study_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    program: ProgramRuntime,
    memory: MemoryRuntime,
) -> StudyRuntimes:
    """Quizzes and reviews (D101), guided sessions (D103), replanning (D106), quick capture
    (D108): launcher (linked to the engine later), program (lock, ticked or follow-up tasks,
    versions), memory (level reflection, stored capture)."""
    return StudyRuntimes(
        quiz=QuizRuntime(session_factory, launcher, program, memory),
        study=StudyRuntime(session_factory, launcher, program, memory),
        replan=ReplanRuntime(session_factory, launcher, program),
        capture=CaptureRuntime(session_factory, launcher, program, memory),
    )


def agent_ports(
    memory: MemoryRuntime,
    research: ResearchRuntime,
    *,
    learning: LearningRuntime,
    program: ProgramRuntime,
    lessons: LessonsRuntime,
    study: StudyRuntimes,
    gap: GapStore = NO_GAP,
    profile: ProfileStore = NO_PROFILE,
    cv_templates: CvTemplateStore = NO_CV_TEMPLATES,
    cv_review: CvReviewStore = NO_CV_REVIEW,
    applications: ApplicationStore = NO_APPLICATIONS,
    kit: KitStore = NO_KIT,
    interviews: InterviewStore = NO_INTERVIEWS,
    committee: CommitteeStore = NO_COMMITTEE,
    radar: RadarStore = NO_RADAR,
    brief: BriefStore = NO_BRIEF,
    projects: ProjectStore = NO_PROJECTS,
    ide: IdeStore = NO_IDE,
    podcast: PodcastStore = NO_PODCAST,
    boss: BossReviewPort = NO_BOSS,
) -> AgentPorts:
    """Composes the agent ports from the services of their features (D82)."""
    ports = AgentPorts(
        memory_gateway(memory),
        web_gateway(research),
        AgentCouncilStore(learning.session_factory, learning.launcher, learning),
        AgentProgramStore(program),
        AgentLessonStore(lessons),
        AgentQuizStore(study.quiz),
        AgentStudyStore(study.study),
        AgentReplanStore(study.replan),
        AgentCaptureStore(study.capture),
        gap,
        profile,
        cv_templates,
        cv_review,
        applications,
        kit,
        interviews,
        committee,
        radar,
        brief,
        projects,
        ide,
        boss=boss,
        podcast=podcast,
    )
    return _persisted_ports(ports, lessons.session_factory)


def _persisted_ports(
    ports: AgentPorts, session_factory: async_sessionmaker[AsyncSession]
) -> AgentPorts:
    return replace(
        ports,
        conversations=AgentConversationStore(session_factory),
        expert_debates=AgentExpertDebates(session_factory),
        lesson_hunt=AgentLessonHuntStore(session_factory),
        oncall=AgentOncallStore(session_factory),
        lesson_updates=AgentLessonUpdatesStore(session_factory),
        linkedin=AgentLinkedInStore(session_factory),
        paper_lab=AgentPaperLabStore(session_factory),
        skill_transfer=AgentSkillTransferStore(session_factory),
        blind_assessment=AgentBlindAssessmentStore(session_factory),
        recruitment_process=AgentRecruitmentStore(session_factory),
        grade_appeals=AgentGradeAppealsStore(session_factory),
        code_trial=AgentCodeTrialStore(session_factory),
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
    """Lesson production (D91): launcher (linked to the engine later), memory (stored lesson),
    research (PDF copies), memory file storage, PDF rendering of our templates."""
    return LessonsRuntime(session_factory, launcher, memory, research, files.storage, publishing)


def scheduler_context(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    lessons: LessonsRuntime,
    replan: ReplanRuntime,
    applications: ApplicationsRuntime,
    daily: DailyJobs,
    book: BookRuntime | None = None,
) -> JobContext:
    """What scheduled tasks receive (D91): base, launcher, lesson production, replanning (weekly
    review, D106), applications (follow-ups, D140), daily (radar readings, D160)."""
    return JobContext(session_factory, launcher, lessons, replan, applications, daily, book)
