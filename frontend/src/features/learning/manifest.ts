import type { FeatureManifest } from "@/shared/lib/feature";
import { CouncilIndexPage } from "./pages/CouncilIndexPage";
import { CouncilPage } from "./pages/CouncilPage";
import { GoalsPage } from "./pages/GoalsPage";

/**
 * Learn: the goals, then the Council (framing, research, debate, proposals) that leads to the
 * program (SPEC 3.1). Program, lessons and library are added under the same section (4.15).
 */
export const learningManifest: FeatureManifest = {
  id: "learning",
  routes: [
    { path: "learn/goals", Component: GoalsPage },
    // Two areas side by side (SPEC 15.2): the page takes the full width of the shell.
    { path: "learn/goals/:goalId/council", Component: CouncilPage, handle: { wide: true } },
    { path: "learn/council", Component: CouncilIndexPage },
  ],
  nav: [
    { section: "learn", labelKey: "learning.nav.goals", path: "/learn/goals", order: 1 },
    { section: "learn", labelKey: "learning.nav.council", path: "/learn/council", order: 2 },
  ],
};
