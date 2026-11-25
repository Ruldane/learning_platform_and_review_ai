import type { FeatureManifest } from "@/shared/lib/feature";
import { DemoDebatePage } from "./pages/DemoDebatePage";

/** Smoke test of the agent engine: reachable at `/demo`, deliberately absent from navigation. */
export const demoManifest: FeatureManifest = {
  id: "demo",
  routes: [{ path: "/demo", Component: DemoDebatePage }],
};
