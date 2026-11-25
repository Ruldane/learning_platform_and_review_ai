import type { FeatureManifest } from "@/shared/lib/feature";

/** The health light has no screen or navigation entry: the app places it in the bar. */
export const healthManifest: FeatureManifest = { id: "health", routes: [] };
