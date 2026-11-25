import type { FeatureManifest } from "@/shared/lib/feature";
import { SharedPlanningPage } from "./pages/SharedPlanningPage";

export const interprogramPlanningManifest: FeatureManifest = {
  id: "interprogram_planning",
  routes: [{ path: "study/shared-planning", Component: SharedPlanningPage }],
  nav: [
    {
      section: "study",
      labelKey: "interprogramPlanning.title",
      path: "/study/shared-planning",
      order: 3.8,
    },
  ],
};
