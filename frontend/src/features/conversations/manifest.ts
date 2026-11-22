import type { FeatureManifest } from "@/shared/lib/feature";
import { TrainingPage } from "./pages/TrainingPage";

export const conversationsManifest: FeatureManifest = {
  id: "conversations",
  routes: [{ path: "etudier/training/:studyId?", Component: TrainingPage, handle: { wide: true } }],
  nav: [{ section: "study", labelKey: "training.title", path: "/etudier/training", order: 1.5 }],
};
