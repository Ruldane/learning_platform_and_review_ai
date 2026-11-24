import type { FeatureManifest } from "@/shared/lib/feature";
import { DecisionLabPage } from "./pages/DecisionLabPage";

export const decisionLabManifest: FeatureManifest = {
  id: "decision_lab",
  routes: [{ path: "learn/decisions", Component: DecisionLabPage }],
  nav: [{ section: "study", labelKey: "decisionLab.title", path: "/learn/decisions", order: 7 }],
};
