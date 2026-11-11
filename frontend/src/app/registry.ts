import { healthManifest } from "@/features/health/manifest";
import { homeManifest } from "@/features/home/manifest";
import { settingsManifest } from "@/features/settings/manifest";
import type { FeatureManifest } from "@/shared/lib/feature";

/** Liste des features : ajouter une feature = un dossier + une ligne ici. */
export const FEATURES: FeatureManifest[] = [homeManifest, healthManifest, settingsManifest];
