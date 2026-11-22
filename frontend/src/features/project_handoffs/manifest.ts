import type { FeatureManifest } from "@/shared/lib/feature";
import { ProjectHandoffsPage } from "./pages/ProjectHandoffsPage";

export const projectHandoffsManifest: FeatureManifest = {
  id: "project_handoffs",
  routes: [{ path: "carriere/transmission-projet", Component: ProjectHandoffsPage }],
  nav: [{
    section: "career", labelKey: "projectHandoffs.title",
    path: "/carriere/transmission-projet", order: 6.3,
  }],
};
