import type { FeatureManifest } from "@/shared/lib/feature";
import { DecisionLabPage } from "./pages/DecisionLabPage";

export const decisionLabManifest: FeatureManifest = {
  id: "decision_lab",
  routes: [{ path: "apprendre/decisions", Component: DecisionLabPage }],
  nav: [{ section: "study", labelKey: "decisionLab.title", path: "/apprendre/decisions", order: 7 }],
};
