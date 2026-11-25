import type { FeatureManifest } from "@/shared/lib/feature";
import { RadarPage } from "./pages/RadarPage";

/**
 * The market radar (SPEC 14.2, the « Carrière » section of the navigation, after the gaps): the
 * launch form, the sweep (running, finished or failed) and the history. `/career/radar`
 * shows the latest sweep; `/career/radar/:runId` opens one, or follows the one running.
 */
export const radarManifest: FeatureManifest = {
  id: "radar",
  routes: [
    { path: "career/radar", Component: RadarPage },
    { path: "career/radar/:runId", Component: RadarPage },
  ],
  nav: [{ section: "career", labelKey: "radar.nav.radar", path: "/career/radar", order: 5 }],
};
