import type { FeatureManifest } from "@/shared/lib/feature";
import { SharedPlanningPage } from "./pages/SharedPlanningPage";

export const interprogramPlanningManifest: FeatureManifest = {
  id: "interprogram_planning",
  routes: [{ path: "etudier/planning-commun", Component: SharedPlanningPage }],
  nav: [
    {
      section: "study",
      labelKey: "interprogramPlanning.title",
      path: "/etudier/planning-commun",
      order: 3.8,
    },
  ],
};
