import type { FeatureManifest } from "@/shared/lib/feature";
import { MissionsPage } from "./pages/MissionsPage";

export const missionsManifest: FeatureManifest = {
  id: "missions",
  routes: [{ path: "carriere/missions", Component: MissionsPage }],
  nav: [{ section: "career", labelKey: "missions.title", path: "/carriere/missions", order: 5.6 }],
};
