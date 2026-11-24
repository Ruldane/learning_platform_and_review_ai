import type { FeatureManifest } from "@/shared/lib/feature";
import { BossPage } from "./pages/BossPage";

export const bossManifest: FeatureManifest = {
  id: "boss",
  routes: [{ path: "learn/programs/:programId/boss", Component: BossPage }],
};
