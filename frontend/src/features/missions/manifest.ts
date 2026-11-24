import type { FeatureManifest } from "@/shared/lib/feature";
import { MissionsPage } from "./pages/MissionsPage";

export const missionsManifest: FeatureManifest = {
  id: "missions",
  routes: [{ path: "career/missions", Component: MissionsPage }],
  nav: [{ section: "career", labelKey: "missions.title", path: "/career/missions", order: 5.6 }],
};
