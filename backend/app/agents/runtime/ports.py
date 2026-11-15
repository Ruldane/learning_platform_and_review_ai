"""Ports des agents regroupés (D82) : tout ce que le moteur emprunte aux features passe par un
seul objet, composé par `app.bootstrap.agent_ports` (le moteur n'importe aucune feature,
contrat 6). Un port de plus = un champ ici, avec sa valeur « non branché », et une ligne dans
`bootstrap.agent_ports`."""

from dataclasses import dataclass

from app.agents.tools.applications_port import NO_APPLICATIONS, ApplicationStore
from app.agents.tools.capture_port import NO_CAPTURE, CaptureStore
from app.agents.tools.committee_port import NO_COMMITTEE, CommitteeStore
from app.agents.tools.council_port import NO_COUNCIL, CouncilStore
from app.agents.tools.cv_review_port import NO_CV_REVIEW, CvReviewStore
from app.agents.tools.cv_template_port import NO_CV_TEMPLATES, CvTemplateStore
from app.agents.tools.gap_port import NO_GAP, GapStore
from app.agents.tools.interview_port import NO_INTERVIEWS, InterviewStore
from app.agents.tools.kit_port import NO_KIT, KitStore
from app.agents.tools.lesson_port import NO_LESSONS, LessonStore
from app.agents.tools.memory_port import NO_MEMORY, MemoryGateway
from app.agents.tools.profile_port import NO_PROFILE, ProfileStore
from app.agents.tools.program_port import NO_PROGRAM, ProgramStore
from app.agents.tools.quiz_port import NO_QUIZ, QuizStore
from app.agents.tools.replan_port import NO_REPLAN, ReplanStore
from app.agents.tools.study_port import NO_STUDY, StudyStore
from app.agents.tools.web_port import NO_WEB, WebGateway


@dataclass(frozen=True)
class AgentPorts:
    memory: MemoryGateway = NO_MEMORY  # mémoire (D68)
    web: WebGateway = NO_WEB  # recherche web (D77)
    council: CouncilStore = NO_COUNCIL  # Conseil d'apprentissage (D84)
    program: ProgramStore = NO_PROGRAM  # programme du Stratège (D86)
    lessons: LessonStore = NO_LESSONS  # leçons du Rédacteur (D90)
    quiz: QuizStore = NO_QUIZ  # quiz de l'Examinateur (D100)
    study: StudyStore = NO_STUDY  # sessions d'étude du Tuteur (D102)
    replan: ReplanStore = NO_REPLAN  # replanification du Stratège (D105)
    capture: CaptureStore = NO_CAPTURE  # capture rapide de l'Archiviste (D108)
    gap: GapStore = NO_GAP  # analyse d'une offre et son écart (D121)
    profile: ProfileStore = NO_PROFILE  # profil maître de l'Archiviste (D124)
    cv_templates: CvTemplateStore = NO_CV_TEMPLATES  # gabarits du Maquettiste (D125)
    cv_review: CvReviewStore = NO_CV_REVIEW  # revue du CV contre une offre (D129)
    applications: ApplicationStore = NO_APPLICATIONS  # fiche créée en une phrase (D141)
    kit: KitStore = NO_KIT  # kit de candidature (D142)
    interviews: InterviewStore = NO_INTERVIEWS  # entretien blanc de l'Intervieweur (D145)
    committee: CommitteeStore = NO_COMMITTEE  # comité de recrutement simulé (D147)


NO_PORTS = AgentPorts()
