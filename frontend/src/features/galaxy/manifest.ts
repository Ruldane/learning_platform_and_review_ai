import type { FeatureManifest } from "@/shared/lib/feature";
import { GalaxyPage } from "./pages/GalaxyPage";

export const galaxyManifest: FeatureManifest = {
  id: "galaxy",
  routes: [{ path: "competences/galaxie", Component: GalaxyPage, handle: { wide: true } }],
  nav: [{ section: "skills", labelKey: "galaxy.nav", path: "/competences/galaxie", order: 1.5 }],
};
