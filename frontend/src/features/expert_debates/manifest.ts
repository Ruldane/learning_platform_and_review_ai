import type { FeatureManifest } from "@/shared/lib/feature";
import { ExpertDebatesPage } from "./pages/ExpertDebatesPage";

export const expertDebatesManifest: FeatureManifest = {
  id: "expert_debates",
  routes: [
    { path: "study/debates", Component: ExpertDebatesPage },
    { path: "study/debates/:debateId", Component: ExpertDebatesPage },
  ],
  nav: [{ section: "study", labelKey: "expertDebates.nav", path: "/study/debates", order: 1.8 }],
};
