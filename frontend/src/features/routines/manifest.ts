import type { FeatureManifest } from "@/shared/lib/feature";
import { RoutinesPage } from "./pages/RoutinesPage";

export const routinesManifest: FeatureManifest = {
  id: "routines",
  routes: [{ path: "reglages/routines", Component: RoutinesPage }],
  nav: [
    { section: "settings", labelKey: "routines.title", path: "/reglages/routines", order: 6.5 },
  ],
};
