"""Grouped agent ports (D82): everything the engine borrows from the features goes through one
single object, composed by `app.bootstrap.agent_ports` (the engine imports no feature,
contract 6). One more port = one field here, with its "not wired" value, and one line in
`bootstrap.agent_ports`."""

from dataclasses import dataclass

from app.agents.tools.applications_port import NO_APPLICATIONS, ApplicationStore
from app.agents.tools.blind_assessment_port import NO_BLIND, BlindAssessmentStore
from app.agents.tools.boss_port import NO_BOSS, BossReviewPort
from app.agents.tools.brief_port import NO_BRIEF, BriefStore
from app.agents.tools.capture_port import NO_CAPTURE, CaptureStore
from app.agents.tools.code_trial_port import NO_CODE_TRIAL, CodeTrialPort
from app.agents.tools.committee_port import NO_COMMITTEE, CommitteeStore
from app.agents.tools.conversation_port import NO_CONVERSATION, ConversationStore
from app.agents.tools.council_port import NO_COUNCIL, CouncilStore
from app.agents.tools.cv_review_port import NO_CV_REVIEW, CvReviewStore
from app.agents.tools.cv_template_port import NO_CV_TEMPLATES, CvTemplateStore
from app.agents.tools.expert_debate_port import NO_EXPERT_DEBATE, ExpertDebateStore
from app.agents.tools.gap_port import NO_GAP, GapStore
from app.agents.tools.grade_appeals_port import NO_APPEALS, GradeAppealsStore
from app.agents.tools.ide_port import NO_IDE, IdeStore
from app.agents.tools.interview_port import NO_INTERVIEWS, InterviewStore
from app.agents.tools.kit_port import NO_KIT, KitStore
from app.agents.tools.lesson_hunt_port import NO_HUNT, LessonHuntStore
from app.agents.tools.lesson_port import NO_LESSONS, LessonStore
from app.agents.tools.lesson_updates_port import NO_LESSON_UPDATE, LessonUpdatePort
from app.agents.tools.linkedin_port import NO_LINKEDIN, LinkedInStore
from app.agents.tools.memory_port import NO_MEMORY, MemoryGateway
from app.agents.tools.oncall_port import NO_ONCALL, OncallPort
from app.agents.tools.paper_lab_port import NO_PAPER_LAB, PaperLabStore
from app.agents.tools.podcast_port import NO_PODCAST, PodcastStore
from app.agents.tools.profile_port import NO_PROFILE, ProfileStore
from app.agents.tools.program_port import NO_PROGRAM, ProgramStore
from app.agents.tools.project_port import NO_PROJECTS, ProjectStore
from app.agents.tools.quiz_port import NO_QUIZ, QuizStore
from app.agents.tools.radar_port import NO_RADAR, RadarStore
from app.agents.tools.recruitment_process_port import NO_RECRUITMENT, RecruitmentStore
from app.agents.tools.replan_port import NO_REPLAN, ReplanStore
from app.agents.tools.skill_transfer_port import NO_TRANSFER, SkillTransferStore
from app.agents.tools.study_port import NO_STUDY, StudyStore
from app.agents.tools.web_port import NO_WEB, WebGateway


@dataclass(frozen=True)
class AgentPorts:
    memory: MemoryGateway = NO_MEMORY  # memory (D68)
    web: WebGateway = NO_WEB  # recherche web (D77)
    council: CouncilStore = NO_COUNCIL  # Conseil d'apprentissage (D84)
    program: ProgramStore = NO_PROGRAM  # Strategist's program (D86)
    lessons: LessonStore = NO_LESSONS  # Writer's lessons (D90)
    quiz: QuizStore = NO_QUIZ  # Examiner's quiz (D100)
    study: StudyStore = NO_STUDY  # Tutor's study sessions (D102)
    replan: ReplanStore = NO_REPLAN  # Strategist's replanning (D105)
    capture: CaptureStore = NO_CAPTURE  # Archivist's quick capture (D108)
    gap: GapStore = NO_GAP  # analysis of an offer and its gap (D121)
    profile: ProfileStore = NO_PROFILE  # Archivist's master profile (D124)
    cv_templates: CvTemplateStore = NO_CV_TEMPLATES  # layout designer's templates (D125)
    cv_review: CvReviewStore = NO_CV_REVIEW  # CV review against an offer (D129)
    applications: ApplicationStore = NO_APPLICATIONS  # record created in one sentence (D141)
    kit: KitStore = NO_KIT  # application kit (D142)
    interviews: InterviewStore = NO_INTERVIEWS  # mock interview by the Interviewer (D145)
    committee: CommitteeStore = NO_COMMITTEE  # simulated hiring committee (D147)
    radar: RadarStore = NO_RADAR  # market radar: survey, reading, extraction (D159)
    brief: BriefStore = NO_BRIEF  # daily brief: resource and advice (D161)
    projects: ProjectStore = NO_PROJECTS  # project brief and evaluation, proof projects (D165)
    ide: IdeStore = NO_IDE  # IDE teacher and generated exercises (D203)
    boss: BossReviewPort = NO_BOSS
    code_trial: CodeTrialPort = NO_CODE_TRIAL
    conversations: ConversationStore = NO_CONVERSATION
    lesson_hunt: LessonHuntStore = NO_HUNT
    oncall: OncallPort = NO_ONCALL
    paper_lab: PaperLabStore = NO_PAPER_LAB
    skill_transfer: SkillTransferStore = NO_TRANSFER
    blind_assessment: BlindAssessmentStore = NO_BLIND
    recruitment_process: RecruitmentStore = NO_RECRUITMENT
    grade_appeals: GradeAppealsStore = NO_APPEALS
    lesson_updates: LessonUpdatePort = NO_LESSON_UPDATE
    expert_debates: ExpertDebateStore = NO_EXPERT_DEBATE
    linkedin: LinkedInStore = NO_LINKEDIN
    podcast: PodcastStore = NO_PODCAST


NO_PORTS = AgentPorts()
