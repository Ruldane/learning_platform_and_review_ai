import type { FeatureManifest } from "@/shared/lib/feature";
import { ProjectionPage } from "./pages/ProjectionPage";

export const futureSelfManifest: FeatureManifest = {
  id: "future_self",
  routes: [{ path: "career/future-self", Component: ProjectionPage }],
  nav: [{ section: "career", labelKey: "futureSelf.title", path: "/career/future-self", order: 6 }],
};
