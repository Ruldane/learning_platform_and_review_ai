import type { FeatureManifest } from "@/shared/lib/feature";
import { GalaxyPage } from "./pages/GalaxyPage";

export const galaxyManifest: FeatureManifest = {
  id: "galaxy",
  routes: [{ path: "skills/galaxy", Component: GalaxyPage, handle: { wide: true } }],
  nav: [{ section: "skills", labelKey: "galaxy.nav", path: "/skills/galaxy", order: 1.5 }],
};
