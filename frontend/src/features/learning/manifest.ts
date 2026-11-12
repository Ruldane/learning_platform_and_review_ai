import type { FeatureManifest } from "@/shared/lib/feature";
import { CouncilIndexPage } from "./pages/CouncilIndexPage";
import { CouncilPage } from "./pages/CouncilPage";
import { GoalsPage } from "./pages/GoalsPage";

/**
 * Apprendre : les objectifs, puis le Conseil (cadrage, recherche, débat, propositions) qui mène au
 * programme (SPEC 3.1). Programme, leçons et bibliothèque s'ajoutent sous la même section (4.15).
 */
export const learningManifest: FeatureManifest = {
  id: "learning",
  routes: [
    { path: "apprendre/objectifs", Component: GoalsPage },
    // Deux zones côte à côte (SPEC 15.2) : la page prend toute la largeur de la coquille.
    { path: "apprendre/objectifs/:goalId/conseil", Component: CouncilPage, handle: { wide: true } },
    { path: "apprendre/conseil", Component: CouncilIndexPage },
  ],
  nav: [
    { section: "learn", labelKey: "learning.nav.goals", path: "/apprendre/objectifs", order: 1 },
    { section: "learn", labelKey: "learning.nav.council", path: "/apprendre/conseil", order: 2 },
  ],
};
