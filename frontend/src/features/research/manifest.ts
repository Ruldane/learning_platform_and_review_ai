import type { FeatureManifest } from "@/shared/lib/feature";
import { ResearchBenchPage } from "./pages/ResearchBenchPage";

/**
 * Recherche web (F5) : l'essai de l'Éclaireur, rangé sous Réglages avec les réglages de recherche
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
