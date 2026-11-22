import type { FeatureManifest } from "@/shared/lib/feature";
import { PaperLabPage } from "./pages/PaperLabPage";

export const paperLabManifest: FeatureManifest = {
  id: "paper_lab",
  routes: [
    { path: "apprendre/articles", Component: PaperLabPage },
    { path: "apprendre/articles/:labId", Component: PaperLabPage },
  ],
  nav: [{ section: "learn", labelKey: "paperLab.title", path: "/apprendre/articles", order: 8 }],
};
