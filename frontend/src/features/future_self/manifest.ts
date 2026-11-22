import type { FeatureManifest } from "@/shared/lib/feature";
import { ProjectionPage } from "./pages/ProjectionPage";

export const futureSelfManifest: FeatureManifest = {
  id: "future_self",
  routes: [{ path: "carriere/futur", Component: ProjectionPage }],
  nav: [{ section: "career", labelKey: "futureSelf.title", path: "/carriere/futur", order: 6 }],
};
