import { accountManifest } from "@/features/account/manifest";
import { applicationsManifest } from "@/features/applications/manifest";
import { authManifest } from "@/features/auth/manifest";
import { blindAssessmentManifest } from "@/features/blind_assessment/manifest";
import { bookManifest } from "@/features/book/manifest";
import { bossManifest } from "@/features/boss/manifest";
import { makeBrainManifest } from "@/features/brain/manifest";
import { codeTrialManifest } from "@/features/code_trial/manifest";
import { calendarManifest } from "@/features/calendar/manifest";
import { captureManifest } from "@/features/capture/manifest";
import { compatibleOffersManifest } from "@/features/compatible_offers/manifest";
import { contradictoryWatchManifest } from "@/features/contradictory_watch/manifest";
import { contributionsManifest } from "@/features/contributions/manifest";
import { conversationsManifest } from "@/features/conversations/manifest";
import { BrainConversation } from "@/features/conversations/pages/BrainConversation";
import { LessonConversation } from "@/features/conversations/pages/LessonConversation";
import { costsManifest } from "@/features/costs/manifest";
import { cvManifest } from "@/features/cv/manifest";
import { dataInvestigationManifest } from "@/features/data_investigation/manifest";
import { datedCommitmentsManifest } from "@/features/dated_commitments/manifest";
import { demoManifest } from "@/features/demo/manifest";
import { errorAtlasManifest } from "@/features/error_atlas/manifest";
import { expertDebatesManifest } from "@/features/expert_debates/manifest";
import { futureSelfManifest } from "@/features/future_self/manifest";
import { galaxyManifest } from "@/features/galaxy/manifest";
import { gradeAppealsManifest } from "@/features/grade_appeals/manifest";
import { gapManifest } from "@/features/gap/manifest";
import { IdeGhostPanel } from "@/features/ghost/pages/IdeGhostPanel";
import { QuizGhostPanel } from "@/features/ghost/pages/QuizGhostPanel";
import { healthManifest } from "@/features/health/manifest";
import { homeManifest } from "@/features/home/manifest";
import { makeIdeManifest } from "@/features/ide/manifest";
import { incidentReplayManifest } from "@/features/incident_replay/manifest";
import { interprogramPlanningManifest } from "@/features/interprogram_planning/manifest";
import { learningManifest } from "@/features/learning/manifest";
import { lessonHuntManifest } from "@/features/lesson_hunt/manifest";
import { lessonUpdatesManifest } from "@/features/lesson_updates/manifest";
import { lessonVariantsManifest } from "@/features/lesson_variants/manifest";
import { LessonUpdates } from "@/features/lesson_updates/pages/LessonUpdates";
import { makeLessonsManifest } from "@/features/lessons/manifest";
import { linkedInDraftsManifest } from "@/features/linkedin_drafts/manifest";
import { missionsManifest } from "@/features/missions/manifest";
import { decisionLabManifest } from "@/features/decision_lab/manifest";
import { routinesManifest } from "@/features/routines/manifest";
import { mcpManifest } from "@/features/mcp/manifest";
import { meetingModulesManifest } from "@/features/meeting_modules/manifest";
import { memoryManifest } from "@/features/memory/manifest";
import { mentorReviewsManifest } from "@/features/mentor_reviews/manifest";
import { messageReviewManifest } from "@/features/message_review/manifest";
import { offerComparisonManifest } from "@/features/offer_comparison/manifest";
import { oncallManifest } from "@/features/oncall/manifest";
import { paperLabManifest } from "@/features/paper_lab/manifest";
import { podcastManifest } from "@/features/podcast/manifest";
import { portfolioManifest } from "@/features/portfolio/manifest";
import { proofPacketsManifest } from "@/features/proof_packets/manifest";
import { programManifest } from "@/features/program/manifest";
import { projectHandoffsManifest } from "@/features/project_handoffs/manifest";
import { projectsManifest } from "@/features/projects/manifest";
import { makeQuizManifest } from "@/features/quiz/manifest";
import { radarManifest } from "@/features/radar/manifest";
import { readingManifest } from "@/features/reading_stack/manifest";
import { recruitmentProcessManifest } from "@/features/recruitment_process/manifest";
import { replanManifest } from "@/features/replan/manifest";
import { researchManifest } from "@/features/research/manifest";
import { settingsManifest } from "@/features/settings/manifest";
import { skillMarketManifest } from "@/features/skill_market/manifest";
import { skillTransferManifest } from "@/features/skill_transfer/manifest";
import { skillsManifest } from "@/features/skills/manifest";
import { studyReturnManifest } from "@/features/study_return/manifest";
import { studyManifest } from "@/features/study/manifest";
import { surpriseInterviewManifest } from "@/features/surprise_interview/manifest";
import type { FeatureManifest } from "@/shared/lib/feature";

/** Liste des features : ajouter une feature = un dossier + une ligne ici. */
export const FEATURES: FeatureManifest[] = [
  authManifest,
  homeManifest,
  healthManifest,
  learningManifest,
  programManifest,
  makeLessonsManifest(LessonConversation, LessonUpdates),
  lessonUpdatesManifest,
  lessonVariantsManifest,
  lessonHuntManifest,
  bookManifest,
  bossManifest,
  paperLabManifest,
  conversationsManifest,
  expertDebatesManifest,
  studyManifest,
  studyReturnManifest,
  podcastManifest,
  makeQuizManifest(QuizGhostPanel),
  captureManifest,
  skillMarketManifest,
  skillsManifest,
  skillTransferManifest,
  gradeAppealsManifest,
  contradictoryWatchManifest,
  errorAtlasManifest,
  galaxyManifest,
  projectsManifest,
  projectHandoffsManifest,
  portfolioManifest,
  compatibleOffersManifest,
  contributionsManifest,
  gapManifest,
  radarManifest,
  futureSelfManifest,
  cvManifest,
  applicationsManifest,
  replanManifest,
  memoryManifest,
  makeBrainManifest(BrainConversation),
  readingManifest,
  settingsManifest,
  routinesManifest,
  calendarManifest,
  messageReviewManifest,
  surpriseInterviewManifest,
  costsManifest,
  accountManifest,
  researchManifest,
  demoManifest,
  linkedInDraftsManifest,
  missionsManifest,
  proofPacketsManifest,
  recruitmentProcessManifest,
  offerComparisonManifest,
  mentorReviewsManifest,
  blindAssessmentManifest,
  interprogramPlanningManifest,
  incidentReplayManifest,
  dataInvestigationManifest,
  datedCommitmentsManifest,
  meetingModulesManifest,
  decisionLabManifest,
  mcpManifest,
  makeIdeManifest(IdeGhostPanel),
  codeTrialManifest,
  oncallManifest,
];
