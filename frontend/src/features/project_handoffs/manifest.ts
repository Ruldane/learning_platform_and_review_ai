import type { FeatureManifest } from "@/shared/lib/feature";
import { ProjectHandoffsPage } from "./pages/ProjectHandoffsPage";

export const projectHandoffsManifest: FeatureManifest = {
  id: "project_handoffs",
  routes: [{ path: "career/project-handoffs", Component: ProjectHandoffsPage }],
  nav: [{
    section: "career", labelKey: "projectHandoffs.title",
    path: "/career/project-handoffs", order: 6.3,
  }],
};
