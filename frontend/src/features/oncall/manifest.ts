import type { FeatureManifest } from "@/shared/lib/feature";
import { OncallPage } from "./pages/OncallPage";

export const oncallManifest: FeatureManifest = {
  id: "oncall",
  routes: [
    { path: "astreinte", Component: OncallPage },
    { path: "astreinte/:incidentId", Component: OncallPage },
  ],
  nav: [{ section: "study", labelKey: "oncall.nav.oncall", path: "/astreinte", order: 6 }],
};
