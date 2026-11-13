import { captureManifest } from "@/features/capture/manifest";
import { demoManifest } from "@/features/demo/manifest";
import { healthManifest } from "@/features/health/manifest";
import { homeManifest } from "@/features/home/manifest";
import { learningManifest } from "@/features/learning/manifest";
import { lessonsManifest } from "@/features/lessons/manifest";
import { memoryManifest } from "@/features/memory/manifest";
import { programManifest } from "@/features/program/manifest";
import { quizManifest } from "@/features/quiz/manifest";
import { replanManifest } from "@/features/replan/manifest";
import { researchManifest } from "@/features/research/manifest";
import { settingsManifest } from "@/features/settings/manifest";
import { skillsManifest } from "@/features/skills/manifest";
import { studyManifest } from "@/features/study/manifest";
import type { FeatureManifest } from "@/shared/lib/feature";

/** Liste des features : ajouter une feature = un dossier + une ligne ici. */
export const FEATURES: FeatureManifest[] = [
  homeManifest,
  healthManifest,
  learningManifest,
  programManifest,
  lessonsManifest,
  studyManifest,
  quizManifest,
  captureManifest,
  skillsManifest,
  replanManifest,
  memoryManifest,
  settingsManifest,
  researchManifest,
  demoManifest,
];
