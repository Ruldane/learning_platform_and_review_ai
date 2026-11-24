import type { FeatureManifest } from "@/shared/lib/feature";
import { PaperLabPage } from "./pages/PaperLabPage";

export const paperLabManifest: FeatureManifest = {
  id: "paper_lab",
  routes: [
    { path: "learn/papers", Component: PaperLabPage },
    { path: "learn/papers/:labId", Component: PaperLabPage },
  ],
  nav: [{ section: "learn", labelKey: "paperLab.title", path: "/learn/papers", order: 8 }],
};
