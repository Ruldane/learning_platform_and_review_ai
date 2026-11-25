import type { FeatureManifest } from "@/shared/lib/feature";
import { RoutinesPage } from "./pages/RoutinesPage";

export const routinesManifest: FeatureManifest = {
  id: "routines",
  routes: [{ path: "settings/routines", Component: RoutinesPage }],
  nav: [
    { section: "settings", labelKey: "routines.title", path: "/settings/routines", order: 6.5 },
  ],
};
