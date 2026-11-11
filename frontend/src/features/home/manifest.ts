import type { FeatureManifest } from "@/shared/lib/feature";
import { HomePage } from "./pages/HomePage";

export const homeManifest: FeatureManifest = {
  id: "home",
  routes: [{ index: true, Component: HomePage }],
  nav: { section: "home", labelKey: "nav.home", path: "/", order: 1 },
};
