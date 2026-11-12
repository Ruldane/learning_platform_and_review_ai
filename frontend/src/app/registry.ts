import { demoManifest } from "@/features/demo/manifest";
import { healthManifest } from "@/features/health/manifest";
import { homeManifest } from "@/features/home/manifest";
import { learningManifest } from "@/features/learning/manifest";
import { memoryManifest } from "@/features/memory/manifest";
import { researchManifest } from "@/features/research/manifest";
import { settingsManifest } from "@/features/settings/manifest";
import type { FeatureManifest } from "@/shared/lib/feature";

/** Liste des features : ajouter une feature = un dossier + une ligne ici. */
export const FEATURES: FeatureManifest[] = [
  homeManifest,
  healthManifest,
  learningManifest,
  memoryManifest,
  settingsManifest,
  researchManifest,
  demoManifest,
];
