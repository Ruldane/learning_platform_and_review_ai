import type { FeatureManifest } from "@/shared/lib/feature";
import { RadarPage } from "./pages/RadarPage";

/**
 * Le radar du marché (SPEC 14.2, section « Carrière » de la navigation, après les écarts) : le
 * formulaire de lancement, le relevé (en cours, fini ou en échec) et l'historique. `/career/radar`
 * montre le dernier relevé ; `/career/radar/:runId` en ouvre un, ou suit celui qui tourne.
 */
export const radarManifest: FeatureManifest = {
  id: "radar",
  routes: [
    { path: "career/radar", Component: RadarPage },
    { path: "career/radar/:runId", Component: RadarPage },
  ],
  nav: [{ section: "career", labelKey: "radar.nav.radar", path: "/career/radar", order: 5 }],
};
