import type { FeatureManifest } from "@/shared/lib/feature";
import { OncallPage } from "./pages/OncallPage";

export const oncallManifest: FeatureManifest = {
  id: "oncall",
  routes: [
    { path: "on-call", Component: OncallPage },
    { path: "on-call/:incidentId", Component: OncallPage },
  ],
  nav: [{ section: "study", labelKey: "oncall.nav.oncall", path: "/on-call", order: 6 }],
};
