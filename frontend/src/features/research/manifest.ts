import type { FeatureManifest } from "@/shared/lib/feature";
import { ResearchBenchPage } from "./pages/ResearchBenchPage";

/**
 * Web search (F5): the Scout's test, filed under Settings with the search settings
 * (D80).
 */
export const researchManifest: FeatureManifest = {
  id: "research",
  routes: [{ path: "settings/search/probe", Component: ResearchBenchPage }],
  nav: [
    {
      section: "settings",
      labelKey: "research.nav.bench",
      path: "/settings/search/probe",
      order: 2.5,
    },
  ],
};
