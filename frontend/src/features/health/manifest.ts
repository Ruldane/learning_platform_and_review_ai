import type { FeatureManifest } from "@/shared/lib/feature";

/** Le voyant de santé n'a ni écran ni entrée de navigation : l'application le place dans la barre. */
export const healthManifest: FeatureManifest = { id: "health", routes: [] };
