import { accountManifest } from "@/features/account/manifest";
import { applicationsManifest } from "@/features/applications/manifest";
import { authManifest } from "@/features/auth/manifest";
import { bookManifest } from "@/features/book/manifest";
import { bossManifest } from "@/features/boss/manifest";
import { makeBrainManifest } from "@/features/brain/manifest";
import { codeTrialManifest } from "@/features/code_trial/manifest";
import { captureManifest } from "@/features/capture/manifest";
import { compatibleOffersManifest } from "@/features/compatible_offers/manifest";
import { contributionsManifest } from "@/features/contributions/manifest";
import { conversationsManifest } from "@/features/conversations/manifest";
import { BrainConversation } from "@/features/conversations/pages/BrainConversation";
import { LessonConversation } from "@/features/conversations/pages/LessonConversation";
import { costsManifest } from "@/features/costs/manifest";
import { cvManifest } from "@/features/cv/manifest";
import { demoManifest } from "@/features/demo/manifest";
import { expertDebatesManifest } from "@/features/expert_debates/manifest";
import { futureSelfManifest } from "@/features/future_self/manifest";
import { galaxyManifest } from "@/features/galaxy/manifest";
import { gapManifest } from "@/features/gap/manifest";
import { IdeGhostPanel } from "@/features/ghost/pages/IdeGhostPanel";
import { QuizGhostPanel } from "@/features/ghost/pages/QuizGhostPanel";
import { healthManifest } from "@/features/health/manifest";
import { homeManifest } from "@/features/home/manifest";
import { makeIdeManifest } from "@/features/ide/manifest";
import { learningManifest } from "@/features/learning/manifest";
import { lessonHuntManifest } from "@/features/lesson_hunt/manifest";
import { lessonUpdatesManifest } from "@/features/lesson_updates/manifest";
import { LessonUpdates } from "@/features/lesson_updates/pages/LessonUpdates";
import { makeLessonsManifest } from "@/features/lessons/manifest";
import { linkedInDraftsManifest } from "@/features/linkedin_drafts/manifest";
import { mcpManifest } from "@/features/mcp/manifest";
import { memoryManifest } from "@/features/memory/manifest";
import { messageReviewManifest } from "@/features/message_review/manifest";
import { oncallManifest } from "@/features/oncall/manifest";
import { paperLabManifest } from "@/features/paper_lab/manifest";
import { podcastManifest } from "@/features/podcast/manifest";
import { programManifest } from "@/features/program/manifest";
import { projectsManifest } from "@/features/projects/manifest";
import { makeQuizManifest } from "@/features/quiz/manifest";
import { radarManifest } from "@/features/radar/manifest";
import { readingManifest } from "@/features/reading_stack/manifest";
import { replanManifest } from "@/features/replan/manifest";
import { researchManifest } from "@/features/research/manifest";
import { settingsManifest } from "@/features/settings/manifest";
import { skillMarketManifest } from "@/features/skill_market/manifest";
import { skillsManifest } from "@/features/skills/manifest";
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
  lessonHuntManifest,
  bookManifest,
  bossManifest,
  paperLabManifest,
  conversationsManifest,
  expertDebatesManifest,
  studyManifest,
  podcastManifest,
  makeQuizManifest(QuizGhostPanel),
  captureManifest,
  skillMarketManifest,
  skillsManifest,
  galaxyManifest,
  projectsManifest,
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
  messageReviewManifest,
  surpriseInterviewManifest,
  costsManifest,
  accountManifest,
  researchManifest,
  demoManifest,
  linkedInDraftsManifest,
  mcpManifest,
  makeIdeManifest(IdeGhostPanel),
  codeTrialManifest,
  oncallManifest,
];
