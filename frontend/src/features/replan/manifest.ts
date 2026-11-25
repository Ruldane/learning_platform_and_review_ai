import type { FeatureManifest } from "@/shared/lib/feature";
import { ReplanPage } from "./pages/ReplanPage";

/**
 * Replanning a program: outside the navigation; it is reached by the « Replanifier » button of the
 * program, by its banner, or by the Strategist's link (`artifact.ready`).
 */
export const replanManifest: FeatureManifest = {
  id: "replan",
  routes: [{ path: "learn/programs/:programId/replan", Component: ReplanPage }],
};
