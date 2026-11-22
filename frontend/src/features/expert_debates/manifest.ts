import type { FeatureManifest } from "@/shared/lib/feature";
import { ExpertDebatesPage } from "./pages/ExpertDebatesPage";

export const expertDebatesManifest: FeatureManifest = {
  id: "expert_debates",
  routes: [
    { path: "etudier/debats", Component: ExpertDebatesPage },
    { path: "etudier/debats/:debateId", Component: ExpertDebatesPage },
  ],
  nav: [{ section: "study", labelKey: "expertDebates.nav", path: "/etudier/debats", order: 1.8 }],
};
