import type { FeatureManifest } from "@/shared/lib/feature";
import { DemoDebatePage } from "./pages/DemoDebatePage";

/** Test de fumée du moteur d'agents : joignable sur `/demo`, volontairement absent de la navigation. */
export const demoManifest: FeatureManifest = {
  id: "demo",
  routes: [{ path: "/demo", Component: DemoDebatePage }],
};
