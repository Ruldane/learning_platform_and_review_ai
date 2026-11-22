import { accountManifest } from "@/features/account/manifest";
import { applicationsManifest } from "@/features/applications/manifest";
import { authManifest } from "@/features/auth/manifest";
import { makeBrainManifest } from "@/features/brain/manifest";
import { captureManifest } from "@/features/capture/manifest";
import { conversationsManifest } from "@/features/conversations/manifest";
import { BrainConversation } from "@/features/conversations/pages/BrainConversation";
import { LessonConversation } from "@/features/conversations/pages/LessonConversation";
import { costsManifest } from "@/features/costs/manifest";
import { cvManifest } from "@/features/cv/manifest";
import { demoManifest } from "@/features/demo/manifest";
import { gapManifest } from "@/features/gap/manifest";
import { healthManifest } from "@/features/health/manifest";
import { homeManifest } from "@/features/home/manifest";
import { ideManifest } from "@/features/ide/manifest";
import { learningManifest } from "@/features/learning/manifest";
import { makeLessonsManifest } from "@/features/lessons/manifest";
import { mcpManifest } from "@/features/mcp/manifest";
import { memoryManifest } from "@/features/memory/manifest";
import { programManifest } from "@/features/program/manifest";
import { projectsManifest } from "@/features/projects/manifest";
import { quizManifest } from "@/features/quiz/manifest";
import { radarManifest } from "@/features/radar/manifest";
import { replanManifest } from "@/features/replan/manifest";
import { researchManifest } from "@/features/research/manifest";
import { settingsManifest } from "@/features/settings/manifest";
import { skillsManifest } from "@/features/skills/manifest";
import { studyManifest } from "@/features/study/manifest";
import type { FeatureManifest } from "@/shared/lib/feature";

/** Liste des features : ajouter une feature = un dossier + une ligne ici. */
export const FEATURES: FeatureManifest[] = [
  authManifest,
  homeManifest,
  healthManifest,
  learningManifest,
  programManifest,
  makeLessonsManifest(LessonConversation),
  conversationsManifest,
  studyManifest,
  quizManifest,
  captureManifest,
  skillsManifest,
  projectsManifest,
  gapManifest,
  radarManifest,
  cvManifest,
  applicationsManifest,
  replanManifest,
  memoryManifest,
  makeBrainManifest(BrainConversation),
  settingsManifest,
  costsManifest,
  accountManifest,
  researchManifest,
  demoManifest,
  mcpManifest,
  ideManifest,
];
